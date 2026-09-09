local function add_structure(f)
    if not f then
        error("TPG container structure definition is nil")
    end

    f.shape_table_data =
    {
        {
            file        = f.ShapeName,
            life        = f.Life,
            username    = f.Name,
            desrt       = f.ShapeNameDestr or "self",
            classname   = f.classname or "lLandVehicle",
            positioning = f.positioning or "BYNORMAL",
        }
    }

    f.mapclasskey = "P0091000076"
    f.attribute = {wsType_Static, wsType_Standing}
    add_surface_unit(f)
end

add_structure({
    Name         = "TPG_10FT_CONTAINER_OPEN_LITE_V1",
    DisplayName  = _("TPG 10ft Shipping Container - Open (Lite)"),
    ShapeName    = "TPG_10FT_CONTAINER_OPEN_LITE",
    Life         = 20,
    Rate         = 20,
    category     = "Fortification",
    SeaObject    = false,
    isPutToWater = false,
    numParking   = 0,
})
