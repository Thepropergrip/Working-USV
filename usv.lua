-- Explosive Uncrewed Surface Vessel


mount_vfs_model_path	(current_mod_path.."/Shapes")
mount_vfs_texture_path  (current_mod_path.."/Textures/usv")
mount_vfs_liveries_path (current_mod_path.."/Liveries")
	
GT = {};
GT_t.ws = 0;

set_recursive_metatable(GT, GT_t.generic_ship)

local IED = {
	category = CAT_SHELLS,
	user_name = _("IED"),
	model_name    = "pula",
	v0    = 1500.0,
	Dv0   = 0.00508,
	Da0     = 0.0005,
	Da1     = 0.0,
	mass      = 4000,
	explosive     = 10000,
	life_time     = 7,
	caliber     = 240.0,
	s         = 0.0,
	j         = 0.0,
	l         = 0.0,
	charTime    = 0,
	cx        = {1.0,0.78,0.60,0.15,1.80},
	k1        = 9.4e-09,
	tracer_off    = 4,
	scale_tracer  = 1,
	
	name = "IED",

	cartridge = 0,
	};
declare_weapon(IED);

GT_t.LN_t._IEDA = {} 
GT_t.LN_t._IEDA.type = 2
GT_t.LN_t._IEDA.xc = 0.585
GT_t.LN_t._IEDA.distanceMin = 1
GT_t.LN_t._IEDA.distanceMax = 30
GT_t.LN_t._IEDA.max_trg_alt = 150
GT_t.LN_t._IEDA.reactionTime = 1
GT_t.LN_t._IEDA.launch_delay = 1
GT_t.LN_t._IEDA.radialDisperse = 2.7;
GT_t.LN_t._IEDA.dispertionReductionFactor = 0.988;
GT_t.LN_t._IEDA.maxShootingSpeed = 30
GT_t.LN_t._IEDA.beamWidth = math.rad(1);
GT_t.LN_t._IEDA.inclination_correction_upper_limit = math.rad(20);
GT_t.LN_t._IEDA.inclination_correction_bias = math.rad(0.4);
GT_t.LN_t._IEDA.sensor = {}
set_recursive_metatable(GT_t.LN_t._IEDA.sensor, GT_t.WSN_t[4])
GT_t.LN_t._IEDA.PL = {}
GT_t.LN_t._IEDA.PL[1] = {}
GT_t.LN_t._IEDA.PL[1].shot_delay = 9
GT_t.LN_t._IEDA.PL[1].ammo_capacity = 12
GT_t.LN_t._IEDA.PL[1].reload_time = 600;
GT_t.LN_t._IEDA.PL[1].type_ammunition=IED.wsTypeOfWeapon
GT_t.LN_t._IEDA.PL[1].shell_name = {"IED"};
GT_t.LN_t._IEDA.PL[1].switch_on_delay = 0.5;
GT_t.LN_t._IEDA.BR = { {pos = {1.2, 0, 0} } }



GT.visual = {}
GT.visual.shape = "usv.edm"
GT.visual.shape_dstr = ""

GT.animation_arguments.radar1_rotation = 11; -- вращение радара 1
GT.radar1_period = 3;
GT.animation_arguments.radar2_rotation = -1; -- вращение радара 2 отсутствует
GT.animation_arguments.radar3_rotation = -1; -- вращение радара 3 отсутствует
GT.animation_arguments.water_propeller = 8;

GT.life = 10;
GT.mass = 9.59e+006;
GT.max_velocity = 15.4333
GT.race_velocity = 15.4333
GT.economy_velocity = 10.2889
GT.economy_distance = 1.1112e+007
GT.race_distance = 2.778e+006
GT.shipLength = 1.7
GT.Width = 1.4
GT.Height = 37.2
GT.Length = 172.34
GT.DeckLevel = 8
GT.X_nose = 3.7412
GT.X_tail = -3.9824
GT.Tail_Width = 1
GT.Gamma_max = 0.35
GT.Om = 0.02
GT.speedup = 0.229734
GT.R_min = 345.6
GT.distFindObstacles = 568.4

GT.numParking = 1
GT.Helicopter_Num_ = 2

-- GT.airWeaponDist = 100000
-- GT.airFindDist = 150000

GT.Landing_Point = {-44.0, 9.93, 0.0}

----------------------------------------------------------------------------------------------------------------------------
--------------  Damage Model 
-----------  Attenzione: gli argument devono essere unici.
GT.DM = {
----- Scafo.
	{ area_name = "TOWER_NOSE",		area_arg = 76,	area_life = 70, area_fire = { pos = {45.0, 4.0, 3.0}, size = 1.5}},
	{ area_name = "TOWER_KORMA", 		area_arg = 73,	area_life = 70, area_fire = { pos = {30.0, 4.0,- 3.0}, size = 1.5}},	
	{ area_name = "Scafo_Poppa_Dx", 		area_arg = 72,	area_life = 60, area_fire = { pos = {-20.0, 2.0, 3.0}, size = 1.5}},
    	{ area_name = "Scafo_Poppa_Sx", 		area_arg = 75,	area_life = 60, area_fire = { pos = {-10.0, 2.0, -3.0}, size = 1.5}},
 -------- Sovrastrutture	
	{ area_name = "Strutture_Poppa",           area_arg = 82,	area_life = 80, area_fire = { pos = {-35.0, 12.0, 0.0}, size = 1.5}},
	{ area_name = "Sala_Comando",	                area_arg = 83,	area_life = 80, area_fire = { pos = {30.0, 12.0, 0.0}, size = 1.5}},
--------- 4 Torri Binate da 380mm	
	{ area_name = "Torre_380_Anton",		area_arg = 96,	area_life = 60, area_fire = { pos = {35.0, 5.0, 0.0}, size =  1.5}},
        { area_name = "Ponte Poppa",		       area_arg = 85,	area_life = 60, area_fire = { pos = {-45.0, 3.0, 0.0}, size = 1.5}}, 	
---- Fletcher sink	
	{ area_name = "Fletcher_Distrutta",    area_arg = 77,	area_life = 60, area_fire = { pos = {5.0, 12.0, 0.0}, size = 2.5}},

}
	


-- weapon systems
GT.WS = {}
local ws;
GT.WS.maxTargetDetectionRange = 100;
GT.WS.radar_type = 102
GT.WS.searchRadarMaxElevation = math.rad(60);
GT.WS.searchRadarFrequencies = {{50.0e6, 54.0e6}, {2.0e9, 2.2e9}}


-- Artillery Guns
ws = GT_t.inc_ws();
GT.WS[ws] = {}
set_recursive_metatable(GT.WS[ws], GT_t.WS_t.ship_FMC5 )
set_recursive_metatable(GT_t.LN_t._IEDA.sensor, GT_t.WSN_t[4])
GT.WS[ws].area = 'TOWER_NOSE'
GT.WS[ws].center = 'CENTER_TOWER_12'
GT.WS[ws].drawArgument1 = 0
GT.WS[ws].drawArgument2 = 1
GT.WS[ws].angles[1][1] = math.rad(170);
GT.WS[ws].angles[1][2] = math.rad(-170);
GT.WS[ws].LN[1].BR[1].connector_name = 'Point_Gun_01'
GT.WS[ws].LN[1].BR[1].recoilArgument = 33;
GT.WS[ws].LN[1].BR[1].recoilTime = 0.2;

ws = GT_t.inc_ws();
GT.WS[ws] = {}
set_recursive_metatable(GT.WS[ws], GT_t.WS_t.ship_FMC5 )
set_recursive_metatable(GT_t.LN_t._IEDA.sensor, GT_t.WSN_t[4])
GT.WS[ws].area = 'TOWER_KORMA'
GT.WS[ws].center = 'CENTER_TOWER_02'
GT.WS[ws].drawArgument1 = 13
GT.WS[ws].drawArgument2 = 14
GT.WS[ws].angles[1][1] = math.rad(-30);
GT.WS[ws].angles[1][2] = math.rad(30);
GT.WS[ws].reference_angle_Y = math.rad(-180);
GT.WS[ws].LN[1].BR[1].connector_name = 'Point_Gun_02'
GT.WS[ws].LN[1].BR[1].recoilArgument = 34;
GT.WS[ws].LN[1].BR[1].recoilTime = 0.2;



GT.Name = "usv"
GT.DisplayName = _("*Explosive Uncrewed Surface USV")
GT.Rate = 4000

GT.Sensors = {  OPTIC = {"long-range naval optics", "long-range naval LLTV", "long-range naval FLIR",},
                RADAR = {
                    "Patriot str",
                    "ticonderoga search radar",
                }
            };

GT.DetectionRange  = GT.airFindDist;
GT.ThreatRange = GT.airWeaponDist;
GT.Singleton   ="no";
GT.mapclasskey = "P0091000353";
GT.attribute = {wsType_Navy,wsType_Ship,wsType_ArmedShip,TICONDEROGA,
                    "Cruisers",
                    "RADAR_BAND1_FOR_ARM",
                    "DetectionByAWACS",
				};
GT.Categories = {
					{name = "Armed Ship"},
					{name = "HelicopterCarrier"}
				};				
				
add_surface_unit(GT)

