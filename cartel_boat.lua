GT = {};
GT_t.ws = 0;

set_recursive_metatable(GT, GT_t.generic_ship)

GT.visual = {}
GT.visual.shape = "SVG-cartel_boat"
GT.visual.shape_dstr = ""

GT.animation_arguments.radar1_rotation = 12; -- Top Radar
GT.radar1_period = 3;
GT.animation_arguments.radar2_rotation = 13; -- Lower Radar
GT.animation_arguments.radar3_rotation = 14; -- Reserved
GT.animation_arguments.luna_lights = -1;

GT.animation_arguments.flag_animation = 11;
GT.animation_arguments.water_propeller = 20;

GT.life = 5
GT.mass = 1000;
GT.max_velocity = 50.52
GT.race_velocity = 50.52
GT.economy_velocity = 15
GT.economy_distance = 300000
GT.race_distance = 200000
GT.shipLength = 11.0
GT.Width = 2.25
GT.Height = 1.25
GT.Length = 11.0
GT.DeckLevel = 0.5
GT.X_nose = 5.5
GT.X_tail = -5.5
GT.Tail_Width = 1.75
GT.Gamma_max = 0.35
GT.Om = 0.05
GT.speedup = 18.0
GT.R_min = 20

GT.distFindObstacles = 150
GT.airWeaponDist = 20000
GT.airFindDist = 30000

GT.exhaust = {}	
	
GT.Name = "cartel_boat"
GT.DisplayName = _("Cartel Drug Smuggling Boat")
GT.Rate = 20
          
GT.DetectionRange  = GT.airFindDist;
GT.ThreatRange = GT.airWeaponDist;
GT.Singleton   ="no";
GT.mapclasskey = "P0091000039";
GT.attribute = {wsType_Navy,wsType_Ship,wsType_CivilShip,wsType_GenericCivShip,
					"low_reflection_vessel",
				};
GT.Categories = {
					{name = "Unarmed Ship"},
				};
add_surface_unit(GT)		