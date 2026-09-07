local function add_static_helicopter(f)
    if not f then
        error("CGAXR static definition missing")
    end

    f.shape_table_data = {
        {
            file        = f.ShapeName,
            life        = f.Life,
            username    = f.Name,
            desrt       = "self",
            classname   = f.classname or "lLandVehicle",
            positioning = f.positioning or "ONLYHEIGTH",
        }
    }

    f.mapclasskey = "P0091000076"
    f.attribute = { wsType_Static, wsType_Standing }
    add_surface_unit(f)
end

add_static_helicopter({
    Name         = "TPG_CGAXR_MC_Drone_Static",
    DisplayName  = _("TPG CGAXR MC Drone"),
    ShapeName    = "CGAXR_MC_Drone",
    Life         = 4,
    Rate         = 5,
    category     = "Helicopters",
    SeaObject    = false,
    isPutToWater = false,
    positioning  = "ONLYHEIGTH",
})
