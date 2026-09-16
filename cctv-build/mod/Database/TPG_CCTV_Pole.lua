-- Genuine static object: no AI vehicle, sensor, camera feed, or weapons.
-- DCS uses the internal category "Fortification" for the Structures menu.
-- ONLYHEIGTH is DCS's spelling; it keeps the pole upright on sloping terrain.
local pole = {
    Name = "TPG_CCTV_Pole",
    DisplayName = _("TPG CCTV Pole"),
    ShapeName = "TPG_CCTV_Pole",
    Life = 30,
    Rate = 1,
    category = "Fortification",
    positioning = "ONLYHEIGTH",
    SeaObject = false,
    isPutToWater = false,
    mapclasskey = "P0091000076",
    attribute = {wsType_Static, wsType_Standing},
    shape_table_data = {
        {
            name = "TPG_CCTV_Pole",
            file = "TPG_CCTV_Pole",
            username = "TPG_CCTV_Pole",
            life = 30,
            desrt = "self",
            classname = "lLandVehicle",
            positioning = "ONLYHEIGTH"
        }
    }
}

-- "self" is the built-in no-separate-wreck reference, not a missing EDM.
-- No countries/coalitions are restricted by this definition.
add_surface_unit(pole)
