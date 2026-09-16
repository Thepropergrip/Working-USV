local plugin_name = "TPG_CCTV_Pole"

declare_plugin(plugin_name, {
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG CCTV Pole"),
    shortName = "TPG CCTV Pole",
    version = "1.0",
    state = "installed",
    info = _("Static CCTV street pole. Original model and source textures by omar-mohamed00; DCS adaptation by TPG. See Credits.txt.")
})

mount_vfs_model_path(current_mod_path .. "/Shapes")
mount_vfs_texture_path(current_mod_path .. "/Textures")
dofile(current_mod_path .. "/Database/TPG_CCTV_Pole.lua")
plugin_done()
