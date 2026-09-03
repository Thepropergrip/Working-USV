from pathlib import Path
import base64, lzma
root=Path(__file__).resolve().parents[1]
parts=sorted((root/'edm-jobs'/'tacoma_lzma_b64').glob('part*.txt'))
if len(parts)!=5:
    raise RuntimeError(f'Expected 5 Tacoma payload chunks, found {len(parts)}')
text=''.join(''.join(p.read_text().split()) for p in parts)
if len(text)%4:
    raise RuntimeError(f'Tacoma payload base64 length {len(text)} is not divisible by 4')
packed=base64.b64decode(text,validate=True)
raw=lzma.decompress(packed)
if len(raw)<8:
    raise RuntimeError('Tacoma compact payload decompressed too small')
out=root/'edm-jobs'/'tacoma_payload_v1.b64'
out.write_text(text)
print(f'[TPG TACOMA] assembled {len(parts)} payload chunks -> {len(text)} base64 chars, {len(packed)} packed bytes, {len(raw)} raw bytes')
