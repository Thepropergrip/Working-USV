import argparse
import struct
from pathlib import Path

# Legacy EDM v10 model::LightNode v1 spotlights, donor-verified against the user's
# working Massun92 watchtower EDMs. DCS 2.9.29 accepts this LightNode family and
# the user's in-game test confirmed real terrain/object illumination.
#
# CRASHFIX 2026-09-05:
# The experimental model::AnimatedProperty<float> Brightness bound to argument 31
# caused a confirmed ModelDesc.dll model::LightNode::apply access violation when
# the Mission Editor preview selected this asset. Keep the proven donor-compatible
# static Property<float> Brightness instead.
#
# Current tuning:
#   isSpot = 1
#   Color = (1.0, 0.9, 0.9)
#   Brightness = 0.55
#   Phi = 1.0
#   Theta = 0.5
#   Distance = 160.0
#   LightNode __VERSION__ = 1

CONNECTOR_PREFIX = "TPG_YARD_FLOOD_"
COUNT = 9
DONOR_COLOR = (1.0, 0.9, 0.9)
SUBSTATION_BRIGHTNESS = 0.55
DONOR_PHI = 1.0
DONOR_THETA = 0.5
SUBSTATION_DISTANCE = 160.0


def u32(buf, off):
    return struct.unpack_from("<I", buf, off)[0]


def parse_header(data):
    if data[:3] != b"EDM":
        raise RuntimeError("Not an EDM file")
    version = struct.unpack_from("<H", data, 3)[0]
    if version != 10:
        raise RuntimeError(f"Expected EDM v10 container, got {version}")
    blob_len = u32(data, 5)
    blob = data[9:9 + blob_len]
    strings = [p.decode("cp1251") for p in blob.split(b"\0")[:-1]]
    return version, strings, 9 + blob_len


def encode_strings(strings):
    return b"".join(s.encode("cp1251") + b"\0" for s in strings)


def ensure_strings(strings):
    required = [
        "LIGHT_NODES",
        "model::LightNode",
        "model::Property<unsigned int>",
        "model::Property<float>",
        "model::Property<osg::Vec3f>",
        "__VERSION__",
        "Color",
        "Brightness",
        "Phi",
        "Theta",
        "Distance",
    ]
    out = list(strings)
    for s in required:
        if s not in out:
            out.append(s)
    return out


def read_nodebase_zero_props(data, off, strings, expected_type):
    type_idx = u32(data, off)
    off += 4
    if type_idx >= len(strings) or strings[type_idx] != expected_type:
        raise RuntimeError(f"Expected {expected_type} at {off - 4}")
    name_len = u32(data, off)
    off += 4
    name = data[off:off + name_len].decode("cp1251")
    off += name_len
    unknown = u32(data, off)
    off += 4
    prop_count = u32(data, off)
    off += 4
    if unknown != 0 or prop_count != 0:
        raise RuntimeError(f"Unexpected connector NodeBase layout for {name}")
    return name, off


def find_connectors(data, body_start, strings):
    if "CONNECTORS" not in strings or "model::Connector" not in strings:
        raise RuntimeError("EDM has no connector group")
    group_idx = strings.index("CONNECTORS")
    connector_type_idx = strings.index("model::Connector")
    needle = struct.pack("<I", group_idx)
    pos = body_start
    candidates = []

    while True:
        pos = data.find(needle, pos)
        if pos < 0:
            break
        if pos + 12 <= len(data):
            count = u32(data, pos + 4)
            first_type = u32(data, pos + 8)
            if 0 < count < 256 and first_type == connector_type_idx:
                off = pos + 8
                parsed = []
                ok = True
                try:
                    for _ in range(count):
                        name, off = read_nodebase_zero_props(data, off, strings, "model::Connector")
                        parent_data = u32(data, off)
                        unknown2 = u32(data, off + 4)
                        off += 8
                        if unknown2 != 0:
                            raise RuntimeError("Unexpected connector trailer")
                        parsed.append((name, parent_data))
                except Exception:
                    ok = False
                if ok:
                    hits = [(n, p) for n, p in parsed if n.startswith(CONNECTOR_PREFIX)]
                    if len(hits) == COUNT:
                        candidates.append((pos, hits))
        pos += 1

    if len(candidates) != 1:
        raise RuntimeError(f"Expected one connector group containing {COUNT} {CONNECTOR_PREFIX}* connectors, found {len(candidates)}")

    group_pos, hits = candidates[0]
    ordered = []
    for name, parent in hits:
        try:
            idx = int(name[len(CONNECTOR_PREFIX):])
        except ValueError:
            raise RuntimeError(f"Bad flood connector name: {name}")
        ordered.append((idx, name, parent))
    ordered.sort()
    if [i for i, _, _ in ordered] != list(range(COUNT)):
        raise RuntimeError(f"Flood connector indices are not 0..{COUNT - 1}: {ordered}")
    return group_pos, ordered


def prop(strings, name, type_name, value):
    out = bytearray(struct.pack("<II", strings.index(type_name), strings.index(name)))
    if type_name == "model::Property<unsigned int>":
        out += struct.pack("<I", int(value))
    elif type_name == "model::Property<float>":
        out += struct.pack("<f", float(value))
    elif type_name == "model::Property<osg::Vec3f>":
        out += struct.pack("<3f", *[float(v) for v in value])
    else:
        raise RuntimeError(f"Unsupported property type {type_name}")
    return bytes(out)


def light_node(strings, name, parent_data):
    out = bytearray()
    out += struct.pack("<I", strings.index("model::LightNode"))
    name_bytes = name.encode("cp1251")
    out += struct.pack("<I", len(name_bytes)) + name_bytes
    out += struct.pack("<I", 0)
    out += struct.pack("<I", 1)
    out += prop(strings, "__VERSION__", "model::Property<unsigned int>", 1)
    out += struct.pack("<I", parent_data)
    out += struct.pack("<B", 1)

    light_props = [
        prop(strings, "Color", "model::Property<osg::Vec3f>", DONOR_COLOR),
        prop(strings, "Brightness", "model::Property<float>", SUBSTATION_BRIGHTNESS),
        prop(strings, "Phi", "model::Property<float>", DONOR_PHI),
        prop(strings, "Theta", "model::Property<float>", DONOR_THETA),
        prop(strings, "Distance", "model::Property<float>", SUBSTATION_DISTANCE),
    ]
    out += struct.pack("<I", len(light_props))
    for p in light_props:
        out += p
    out += struct.pack("<B", 0)
    return bytes(out)


def inject(path):
    path = Path(path)
    data = path.read_bytes()
    version, original_strings, body_start = parse_header(data)

    if "LIGHT_NODES" in original_strings and b"TPG_MASSUN_FLOOD_" in data:
        raise RuntimeError("Massun-style LightNodes already injected")

    strings = ensure_strings(original_strings)
    group_pos, connectors = find_connectors(data, body_start, original_strings)
    group_count_pos = group_pos - 4
    if group_count_pos < body_start:
        raise RuntimeError("Invalid render-item group count position")
    old_group_count = u32(data, group_count_pos)
    if not (1 <= old_group_count <= 8):
        raise RuntimeError(f"Implausible render-item group count {old_group_count}")

    body = bytearray(data[body_start:])
    struct.pack_into("<I", body, group_count_pos - body_start, old_group_count + 1)

    group = bytearray(struct.pack("<II", strings.index("LIGHT_NODES"), COUNT))
    for idx, connector_name, parent_data in connectors:
        group += light_node(strings, f"TPG_MASSUN_FLOOD_{idx:02d}", parent_data)
        print(f"Inject light {idx}: connector={connector_name} parentData={parent_data} brightness={SUBSTATION_BRIGHTNESS} distance={SUBSTATION_DISTANCE}")
    body += group

    string_blob = encode_strings(strings)
    rebuilt = b"EDM" + struct.pack("<H", version) + struct.pack("<I", len(string_blob)) + string_blob + bytes(body)
    if rebuilt.count(b"TPG_MASSUN_FLOOD_") != COUNT:
        raise RuntimeError("Injected light names failed validation")
    if b"model::LightNode" not in rebuilt or b"LIGHT_NODES" not in rebuilt:
        raise RuntimeError("Injected LightNode strings missing")

    path.write_bytes(rebuilt)
    print(f"Injected {COUNT} crash-safe static legacy LightNode v1 spotlights into {path.name}")
    print(f"Brightness={SUBSTATION_BRIGHTNESS}; distance={SUBSTATION_DISTANCE} m")
    print(f"EDM size: {len(data)} -> {len(rebuilt)} bytes; render-item groups {old_group_count} -> {old_group_count + 1}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("edm")
    args = ap.parse_args()
    inject(args.edm)
