declare_plugin("TPG_CGAXR_MC_Drone_Static",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG CGAXR MC Drone Static"),
    shortName = "TPG_CGAXR_MC_Drone_Static",
    version = "1.0.0",
    state = "installed",
    info = _("CGAXR MC Drone high-detail static asset for DCS World."),
})

mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")

dofile(current_mod_path.."/Database/CGAXR_MC_Drone_Static.lua")

plugin_done()
