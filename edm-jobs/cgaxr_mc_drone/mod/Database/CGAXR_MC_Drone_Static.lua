local unit = {
    Name = "TPG_CGAXR_MC_Drone_Static",
    DisplayName = _("TPG CGAXR MC Drone"),
    ShapeName = "CGAXR_MC_Drone",
    Rate = 1,
    category = "Helicopters",
    canExplode = false,
    mapclasskey = "P0091000025",
    life = 8,
    positioning = "BYNORMAL",
    classname = "lLandVehicle",
    desrt = "",
    shape_table_data = {
        {
            file = "CGAXR_MC_Drone",
            username = "TPG CGAXR MC Drone",
            desrt = "",
            classname = "lLandVehicle",
            positioning = "BYNORMAL",
        },
    },
}

add_surface_unit(unit)
