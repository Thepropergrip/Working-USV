-- TPG MAGURA weapon-USV proof of concept
-- EXPERIMENTAL: intentionally artificial flight model. Do not promote without DCS/Tacview validation.
-- Requires the existing MAGURA package that mounts MAGURA_W6_SeaDragon_R73.edm.

local WPN_NAME = "TPG_MAGURA_WEAPON_USV_POC"

local wpn = {
    category        = CAT_MISSILES,
    name            = WPN_NAME,
    user_name       = "TPG MAGURA Weapon-USV POC",
    display_name    = "TPG MAGURA Weapon-USV POC",
    display_name_short = "MAGURA-USV",
    model           = "MAGURA_W6_SeaDragon_R73",
    mass            = 1000.0,
    wsTypeOfWeapon  = {wsType_Weapon, wsType_Missile, wsType_AS_Missile, WSTYPE_PLACEHOLDER},

    -- Treat it as a self-homing anti-surface weapon. The visible geometry is a boat;
    -- the invisible FM is deliberately closer to a huge, slow lifting body.
    class_name = "wAmmunitionSelfHoming",
    scheme     = "AGM-114LS",

    Escort     = 0,
    Head_Type  = 2,
    sigma      = {1.0, 1.0, 1.0},
    aim_sigma  = 0.25,

    M          = 1000.0,
    H_min      = -1,
    H_max      = 200.0,
    H_min_t    = 0.0,
    D_min      = 25.0,
    D_max      = 25000.0,
    Range_max  = 25000.0,
    Life_Time  = 1800.0,
    Nr_max     = 3.0,
    v_min      = 10.0,
    v_mid      = 22.0,
    Mach_max   = 0.12,

    Reflection = 0.15,
    KillDistance = 2.0,

    shape_table_data = {{
        name     = WPN_NAME,
        file     = "MAGURA_W6_SeaDragon_R73",
        life     = 1,
        fire     = {0, 1},
        username = "TPG MAGURA Weapon-USV POC",
        index    = WSTYPE_PLACEHOLDER,
    }},

    -- The first pass intentionally exaggerates virtual lift so 20-25 m/s remains viable.
    -- Visible hull dimensions do NOT correspond to these aerodynamic reference values.
    fm = {
        mass        = 1000.0,
        caliber     = 1.0,
        L           = 5.5,
        I           = 2600.0,
        S           = 22.0,
        Ma          = 0.15,
        Mw          = 0.35,
        Ma_x        = 0.08,
        Mw_x        = 0.15,
        Sw          = 22.0,
        Sm          = 22.0,
        maxAoa      = math.rad(45.0),
        finsTau     = 0.15,
        dCydA       = {1.65, 1.65},
        cx_coeff    = {0.02, 0.02, 0.02, 0.03, 0.04},
        release_rnd = 0.0,
        wind_time   = 0.0,
        wind_sigma  = 0.0,
    },

    -- Long, weak "motor": intended to maintain USV-like speed instead of accelerate like a missile.
    engine = {
        fuel_mass    = 450.0,
        impulse      = 35.0,
        boost_time   = 0.0,
        work_time    = 1200.0,
        boost_factor = 0.0,
        nozzle_position = {{-2.3, 0.0, 0.0}},
        nozzle_orientationXYZ = {{1.0, 0.0, 0.0}},
        tail_width   = 0.0,
        smoke_color  = {0.0, 0.0, 0.0},
        smoke_transparency = 0.0,
        custom_smoke_dissipation_factor = 0.0,
    },

    -- Active-radar surrogate: maximum turn rate is intentionally modest to resemble a fast boat.
    sensor = {
        delay          = 0.0,
        op_time        = 1800.0,
        FOV            = math.rad(120.0),
        max_w_LOS      = math.rad(35.0),
        sens_near_dist = 5.0,
        sens_far_dist  = 30000.0,
        aim_sigma      = 0.25,
        ccm_k0         = 0.0,
        hoj            = 0,
    },

    autopilot = {
        delay       = 0.05,
        op_time     = 1800.0,
        K           = 0.9,
        Kg          = 0.8,
        Ki          = 0.0,
        finsLimit   = 0.22,
        useJumpByDefault = 0,
        J_Power_K   = 0.8,
        J_Diff_K    = 0.35,
        J_Int_K     = 0.0,
        J_Angle_K   = 0.3,
        hKp_err     = 0.08,
        hKp_err_croll = 0.04,
        Kx          = 0.02,
        Kxd         = 0.01,
        K_err_mlt   = 0.15,
        K_roll_diff_mlt = 0.2,
        max_roll    = math.rad(10.0),
        max_start_y_vel = 1.0,
        gload_limit = 2.0,
    },

    -- Small HE payload for first tests; enough to generate an obvious impact without
    -- using an exaggerated ship-killing charge while guidance is still unproven.
    warhead = {
        mass                = 300.0,
        expl_mass           = 300.0,
        other_factors       = {1.0, 1.0, 1.0},
        obj_factors         = {1.0, 1.0},
        concrete_factors    = {1.0, 1.0, 1.0},
        cumulative_factor   = 0.0,
        cumulative_thickness= 0.0,
        piercing_mass       = 60.0,
        caliber             = 1000.0,
    },

    warhead_air = {
        mass                = 300.0,
        expl_mass           = 300.0,
        other_factors       = {1.0, 1.0, 1.0},
        obj_factors         = {1.0, 1.0},
        concrete_factors    = {1.0, 1.0, 1.0},
        cumulative_factor   = 0.0,
        cumulative_thickness= 0.0,
        piercing_mass       = 60.0,
        caliber             = 1000.0,
    },

    proximity_fuze = {
        arm_delay = 0.5,
        radius    = 1.5,
    },
}

declare_weapon(wpn)

TPG_MAGURA_WEAPON_USV_POC = wpn
