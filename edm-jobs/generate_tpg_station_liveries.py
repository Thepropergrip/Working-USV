from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import argparse, json, os
import arabic_reshaper
from bidi.algorithm import get_display

ap=argparse.ArgumentParser()
ap.add_argument('--output',required=True)
args=ap.parse_args()
OUT=Path(args.output); OUT.mkdir(parents=True,exist_ok=True)

FONT_LAT=Path(r'C:\Windows\Fonts\arialbd.ttf')
FONT_REG=Path(r'C:\Windows\Fonts\arial.ttf')
if not FONT_LAT.exists():
    FONT_LAT=Path(r'C:\Windows\Fonts\segoeuib.ttf')
if not FONT_REG.exists():
    FONT_REG=Path(r'C:\Windows\Fonts\segoeui.ttf')

C={
 'red':(112,18,15),'black':(15,17,18),'charcoal':(28,31,33),'white':(232,230,218),
 'cream':(232,215,172),'green':(31,235,82),'blue':(18,58,112),'orange':(196,74,18),
 'cyan':(28,128,165),'grey':(178,177,167),'darkgreen':(19,72,38)
}

LOCALES={
 'USA':{
  'brand':'TPG','tag':'FUEL + LUUUUBE',
  'grades':[('REGULAR','87','$3.95'),('PLUS','89','$4.15'),('PREMIUM','93','$4.45')],'unit':'USD / GAL',
  'footer':'OPEN 24/7  |  AIR  |  ICE','welcome':'WELCOME','pay':'PAY HERE','nosmoke':'NO SMOKING',
  'doorhours':'OPEN 24/7','push':'PUSH','airvac':'AIR + VAC','propane':'PROPANE','atm':'ATM','ice':'ICE',
  'news':'NEWS','fire':'FIRE','aframe':'NO AFTERBURNER\nUNDER CANOPY',
  'ads':[('TACTICAL','TAQUITOS','2 FOR $3.49'),('HOT COFFEE','','BAD DECISIONS'),
         ('LUCKY-ish','TICKETS',''),('BUGS LOST.','','WINDSHIELD WON.')],'rtl':False
 },
 'Russia':{
  'brand':'TPG','tag':'ТОПЛИВО + СЕРВИС',
  'grades':[('БЕНЗИН','АИ-92','56.90'),('БЕНЗИН','АИ-95','61.30'),('БЕНЗИН','АИ-100','78.50')],'unit':'₽ / Л',
  'footer':'КРУГЛОСУТОЧНО  |  ВОЗДУХ  |  ЛЁД','welcome':'ДОБРО ПОЖАЛОВАТЬ','pay':'ОПЛАТА ЗДЕСЬ',
  'nosmoke':'НЕ КУРИТЬ','doorhours':'КРУГЛОСУТОЧНО','push':'ТОЛКАТЬ','airvac':'ВОЗДУХ + ПЫЛЕСОС',
  'propane':'ПРОПАН','atm':'БАНКОМАТ','ice':'ЛЁД','news':'ПРЕССА','fire':'ОГНЕТУШИТЕЛЬ',
  'aframe':'БЕЗ ФОРСАЖА\nПОД НАВЕСОМ',
  'ads':[('ТАКТИЧЕСКИЕ','ТАКИТОС','2 ЗА 299 ₽'),('ГОРЯЧИЙ КОФЕ','','СОМНИТЕЛЬНЫЕ РЕШЕНИЯ'),
         ('СЧАСТЛИВЫЙ БИЛЕТ','ЛОТЕРЕЯ',''),('НАСЕКОМЫМ — НЕТ','','СТЕКЛО ЧИСТОЕ')],'rtl':False
 },
 'Syria':{
  'brand':'TPG','tag':'وقود + خدمة',
  'grades':[('عادي','90','12,000'),('ممتاز','95','14,500'),('سوبر','98','17,000')],'unit':'ل.س / لتر',
  'footer':'مفتوح 24/7  |  هواء  |  ثلج','welcome':'أهلاً وسهلاً','pay':'الدفع هنا','nosmoke':'ممنوع التدخين',
  'doorhours':'مفتوح 24/7','push':'ادفع','airvac':'هواء + مكنسة','propane':'غاز','atm':'صراف','ice':'ثلج',
  'news':'صحف','fire':'طفاية','aframe':'ممنوع الحارق اللاحق\nتحت المظلة',
  'ads':[('تاكيتوس تكتيكية','','2 بـ 15,000 ل.س'),('قهوة ساخنة','','قرارات سيئة'),
         ('تذكرة الحظ','يانصيب',''),('وداعاً للحشرات','','زجاج نظيف')],'rtl':True
 }
}

def shape(text,locale):
    if locale!='Syria':
        return text
    out=[]
    for line in text.split('\n'):
        out.append(get_display(arabic_reshaper.reshape(line)))
    return '\n'.join(out)

def font(size,bold=True):
    return ImageFont.truetype(str(FONT_LAT if bold else FONT_REG),size=size)

def fit(draw,text,locale,max_w,max_h,bold=True,max_size=220,min_size=16):
    text=shape(text,locale)
    for size in range(max_size,min_size-1,-2):
        f=font(size,bold)
        parts=text.split('\n')
        boxes=[draw.textbbox((0,0),p,font=f) for p in parts]
        widths=[b[2]-b[0] for b in boxes]; heights=[b[3]-b[1] for b in boxes]
        th=sum(heights)+max(0,len(parts)-1)*int(size*.18)
        if max(widths or [0])<=max_w and th<=max_h:
            return f,text
    return font(min_size,bold),text

def centered(draw,xy,text,locale,fill,max_w,max_h,font_obj=None):
    if font_obj is None:
        font_obj,text=fit(draw,text,locale,max_w,max_h)
    else:
        text=shape(text,locale)
    draw.multiline_text(xy,text,font=font_obj,fill=fill,anchor='mm',align='center',spacing=max(2,int(font_obj.size*.18)))

def save(root,name,locale,size,painter):
    img=Image.new('RGB',size,(32,32,32)); d=ImageDraw.Draw(img); painter(img,d)
    root.mkdir(parents=True,exist_ok=True)
    p=root/f'{name}_{locale}.png'; img.save(p,optimize=True,compress_level=9)
    return p.name

def make_locale(locale,cfg):
    root=OUT/locale; files=[]
    def pylon(img,d):
        W,H=img.size
        d.rounded_rectangle((4,4,W-4,H-4),radius=22,fill=C['grey'],outline=C['black'],width=12)
        d.rectangle((18,18,W-18,245),fill=C['red'])
        centered(d,(W//2,92),cfg['brand'],'USA',C['white'],W-100,100,font(80))
        centered(d,(W//2,188),cfg['tag'],locale,C['black'],W-80,70)
        y0=245; rowh=145; cols=[C['green'],C['cream'],C['red']]
        for i,(lab,octn,price) in enumerate(cfg['grades']):
            y=y0+i*rowh
            d.rectangle((28,y,W-28,y+rowh-14),fill=C['black'])
            centered(d,(220,y+48),lab,locale,C['cream'],350,52)
            centered(d,(220,y+104),octn,locale,cols[i],300,48)
        unit_y=y0+3*rowh+12
        d.rectangle((28,unit_y,W-28,unit_y+72),fill=C['blue'])
        centered(d,(W//2,unit_y+36),cfg['unit'],locale,C['white'],W-90,46)
        foot_y=unit_y+84
        d.rectangle((28,foot_y,W-28,H-28),fill=C['charcoal'])
        centered(d,(W//2,(foot_y+H-28)//2),cfg['footer'],locale,C['white'],W-100,86)
    files.append(save(root,'TPG_GS_L10N_PYLON',locale,(1120,1000),pylon))

    def price(img,d):
        W,H=img.size; d.rectangle((0,0,W,H),fill=C['black'])
        for (_,_,val),y in zip(cfg['grades'],(H*.17,H*.50,H*.83)):
            centered(d,(W/2,y),val,locale,C['green'],W-24,H*.24)
    files.append(save(root,'TPG_GS_L10N_PRICELED',locale,(420,660),price))

    def simple(name,text,size,bg,fg,border=None):
        def paint(img,d):
            d.rectangle((0,0,img.width,img.height),fill=bg)
            if border:
                d.rectangle((2,2,img.width-3,img.height-3),outline=border,width=max(3,img.height//28))
            centered(d,(img.width/2,img.height/2),text,locale,fg,img.width-30,img.height-24)
        files.append(save(root,name,locale,size,paint))

    simple('TPG_GS_L10N_STORE_SIGN',cfg['brand']+'  '+cfg['tag'],(2200,170),C['red'],C['white'],C['charcoal'])
    simple('TPG_GS_L10N_CANOPY_SIGN',cfg['brand']+'  '+cfg['tag'],(2400,100),C['charcoal'],C['white'])
    simple('TPG_GS_L10N_PUMP_SCREEN',cfg['welcome'],(720,300),C['darkgreen'],C['green'],C['grey'])
    simple('TPG_GS_L10N_PAY',cfg['pay'],(900,260),C['blue'],C['white'])
    simple('TPG_GS_L10N_NOSMOKE',cfg['nosmoke'],(900,250),C['cream'],C['black'])

    gcols=[C['green'],C['cream'],C['red']]
    for i,(lab,octn,val) in enumerate(cfg['grades']):
        def grade(img,d,lab=lab,octn=octn,col=gcols[i]):
            d.rectangle((0,0,img.width,img.height),fill=C['white'])
            d.rectangle((0,0,img.width,95),fill=col)
            centered(d,(img.width/2,47),lab,locale,C['black'] if col!=C['red'] else C['white'],img.width-24,70)
            centered(d,(img.width/2,230),octn,locale,C['black'],img.width-30,170)
        files.append(save(root,f'TPG_GS_L10N_GRADE{i+1}',locale,(420,420),grade))

    simple('TPG_GS_L10N_DOOR_HOURS',cfg['doorhours'],(900,230),C['blue'],C['white'])
    simple('TPG_GS_L10N_DOOR_PUSH',cfg['push'],(500,270),C['cream'],C['black'])
    simple('TPG_GS_L10N_AIRVAC',cfg['airvac'],(1200,280),C['blue'],C['white'])
    simple('TPG_GS_L10N_PROPANE',cfg['propane'],(1100,280),C['red'],C['white'])
    simple('TPG_GS_L10N_ATM',cfg['atm'],(640,260),C['blue'],C['white'])
    simple('TPG_GS_L10N_ICE',cfg['ice'],(600,280),C['blue'],C['white'])
    simple('TPG_GS_L10N_NEWS',cfg['news'],(600,280),C['green'],C['white'])
    simple('TPG_GS_L10N_FIRE',cfg['fire'],(640,300),C['red'],C['white'])
    simple('TPG_GS_L10N_AFRAME',cfg['aframe'],(1100,760),C['orange'],C['cream'],C['charcoal'])

    specs=[('AD_TACO',C['orange']),('AD_COFFEE',C['charcoal']),('AD_LOTTO',C['green']),('AD_WIPER',C['blue'])]
    for (nm,bg),(l1,l2,l3) in zip(specs,cfg['ads']):
        def ad(img,d,l1=l1,l2=l2,l3=l3,bg=bg,nm=nm):
            d.rectangle((0,0,img.width,img.height),fill=bg)
            d.rectangle((8,8,img.width-9,img.height-9),outline=C['charcoal'],width=16)
            if l1: centered(d,(img.width/2,115),l1,locale,C['white'],img.width-70,120)
            if l2: centered(d,(img.width/2,315),l2,locale,C['white'],img.width-70,165)
            if l3: centered(d,(img.width/2,535),l3,locale,C['cream'],img.width-70,120)
            if nm=='AD_TACO':
                for x in (310,450,590): d.rounded_rectangle((x,355,x+100,500),radius=40,fill=C['cream'])
            elif nm=='AD_COFFEE':
                d.rounded_rectangle((360,300,640,470),radius=35,fill=C['cream']); d.ellipse((610,330,760,470),outline=C['cream'],width=24)
            elif nm=='AD_LOTTO':
                for x in (280,440,600): d.rounded_rectangle((x,300,x+120,475),radius=16,fill=C['cream'])
            else:
                d.rounded_rectangle((260,300,760,480),radius=45,fill=C['cyan']); d.line((300,440,720,330),fill=C['charcoal'],width=22)
        files.append(save(root,'TPG_GS_L10N_'+nm,locale,(1024,680),ad))
    return files

manifest={}
for locale,cfg in LOCALES.items():
    manifest[locale]=make_locale(locale,cfg)
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('[TPG] generated livery textures', {k:len(v) for k,v in manifest.items()})
