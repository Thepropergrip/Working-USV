-- Isolated launcher for TPG MAGURA weapon-USV proof of concept.
-- It intentionally reuses the existing MAGURA W6 / Sea Dragon hull and LEFT R-73 connector.
-- The launcher itself is only a test carrier; the launched object is the weapon-USV.

GT = {}
GT_t.ws = 0
set_recursive_metatable(GT, GT_t.generic_ship)

GT.visual = {}
GT.visual.shape = "MAGURA_W6_SeaDragon_R73"
GT.visual.shape_dstr = ""

GT.life = 8
GT.mass = 1100
GT.max_velocity = 22.0
GT.race_velocity = 22.0
GT.economy_velocity = 15.0
GT.economy_distance = 500000
GT.race_distance = 100000
GT.shipLength = 5.5
GT.Width = 1.6
GT.Height = 1.5
GT.Length = 5.5
GT.DeckLevel = 0.5
GT.X_nose = 2.8
GT.X_tail = -2.7
GT.Tail_Width = 1.0
GT.Gamma_max = 0.20
GT.Om = 0.12
GT.speedup = 1.5
GT.R_min = 6.0
GT.distFindObstacles = 20.0
GT.riverCraft = true
GT.sensor = {height = 1.0}
GT.IR_emission_coeff = 0.03
GT.RCS = 1.0

GT.WS = {}
GT.WS.maxTargetDetectionRange = 30000

local ws = GT_t.inc_ws()
GT.WS[ws] = {}
GT.WS[ws].pos = {0.0, 0.7, 0.0}
GT.WS[ws].angles = {
    {math.rad(180), math.rad(-180), math.rad(-8), math.rad(8)}
}
GT.WS[ws].reference_angle_Z = 0
GT.WS[ws].moveable = false
GT.WS[ws].LN = {}
GT.WS[ws].LN[1] = {}
GT.WS[ws].LN[1].type = 8
GT.WS[ws].LN[1].distanceMin = 50
GT.WS[ws].LN[1].distanceMax = 25000
GT.WS[ws].LN[1].reactionTime = 0.5
GT.WS[ws].LN[1].launch_delay = 0.5
GT.WS[ws].LN[1].show_external_missile = false
GT.WS[ws].LN[1].external_tracking_awacs = false
GT.WS[ws].LN[1].max_number_of_missiles_channels = 1
GT.WS[ws].LN[1].sensor = {}
set_recursive_metatable(GT.WS[ws].LN[1].sensor, GT_t.WSN_t[0])

GT.WS[ws].LN[1].PL = {}
GT.WS[ws].LN[1].PL[1] = {}
GT.WS[ws].LN[1].PL[1].ammo_capacity = 1
GT.WS[ws].LN[1].PL[1].type_ammunition = TPG_MAGURA_WEAPON_USV_POC.wsTypeOfWeapon
GT.WS[ws].LN[1].PL[1].name_ammunition = TPG_MAGURA_WEAPON_USV_POC.shape_table_data[1].username
GT.WS[ws].LN[1].PL[1].reload_time = 36000
GT.WS[ws].LN[1].PL[1].shot_delay = 36000

GT.WS[ws].LN[1].BR = {
    {connector_name = "POINT_R73_L"}
}

GT.Name = "TPG_MAGURA_WEAPON_USV_POC_LAUNCHER"
GT.DisplayName = _("TPG MAGURA Weapon-USV POC Launcher")
GT.DisplayNameShort = _("MAGURA USV POC")
GT.Rate = 20

GT.Sensors = {
    OPTIC = {
        "long-range naval optics",
        "long-range naval LLTV",
        "long-range naval FLIR",
    },
}

GT.DetectionRange = 30000
GT.ThreatRange = 25000
GT.Singleton = "no"
GT.mapclasskey = "P0091000039"
GT.attribute = {
    wsType_Navy, wsType_Ship, wsType_ArmedShip, wsType_GenericLightArmoredShip,
    "low_reflection_vessel",
    "Light armed ships",
    "Armed Ship",
    "Naval",
    "All",
    "Ships",
    "Armed ships",
    "NonAndLightArmoredUnits",
    "NonArmoredUnits",
}
GT.Categories = {
    {name = "Armed Ship"},
}
GT.tags = {"Fast Attack Craft"}

add_surface_unit(GT)
