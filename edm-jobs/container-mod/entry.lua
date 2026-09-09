declare_plugin("TPG_10FT_CONTAINER_OPEN_LITE_V1",
{
    installed   = true,
    dirName     = current_mod_path,
    displayName = _("TPG 10ft Shipping Container Open - Lite"),
    shortName   = "TPG 10ft Container Lite",
    version     = "1.0.0",
    state       = "installed",
    info        = _("Optimized open 10-foot shipping container static asset for DCS World."),
})

mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")

dofile(current_mod_path.."/Database/db_objects.lua")

plugin_done()
