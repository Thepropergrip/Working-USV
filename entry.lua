declare_plugin("Explosive Uncrewed Surface Vessel",
{
--image     	 = "FC.bmp",
installed 	 = true, -- if false that will be place holder , or advertising
dirName	  	 = current_mod_path,
version		 = "beta",		 
state		 = "installed",


Skins	= 
	{
		{
			name	= "Explosive Uncrewed Surface Vessel",
			dir		= "Theme"
		},
	},

}
)

-- ---------------------------------------------------------------------------------------
dofile(current_mod_path..'/usv.lua')
dofile(current_mod_path..'/saildrone usv.lua')
dofile(current_mod_path..'/usv_ex.lua')
dofile(current_mod_path..'/saildrone usv_ex.lua')

plugin_done()-- finish declaration , clear temporal data
