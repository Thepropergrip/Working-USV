declare_plugin("TPG_MAGURA_WEAPON_USV_POC",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG MAGURA Weapon-USV POC"),
    shortName = "TPG MAGURA USV POC",
    developerName = "TPG",
    version = "0.0.1-poc",
    state = "installed",
    info = _("Experimental anti-ship weapon object using the existing MAGURA W6 / Sea Dragon hull as the rendered body."),
})

-- Dependency by design: the existing MAGURA mod mounts the EDM and textures.
-- This POC only declares the new weapon object.
dofile(current_mod_path .. "/Database/TPG_MAGURA_WEAPON_USV_POC.lua")

plugin_done()
