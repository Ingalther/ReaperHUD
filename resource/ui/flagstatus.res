// The Reaper HUD - made by Ingalther. Licence: CC BY-NC-SA 4.0 (credit required, no selling).
"Resource/UI/FlagStatus.res"
{
	"Arrow"
	{
		"ControlName"		"CTFArrowPanel"
		"fieldName"		"Arrow"
		"xpos"		"48"
		"ypos"		"0"
		"zpos"		"1"
		"wide"		"64"
		"tall"		"64"
		"visible"		"1"
		"enabled"		"1"
		"scaleImage"		"1"
	}
	"Briefcase"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"Briefcase"
		"xpos"		"63"
		"ypos"		"15"
		"zpos"		"2"
		"wide"		"34"
		"tall"		"34"
		"visible"		"1"
		"enabled"		"1"
		"image"		"../hud/objectives_flagpanel_briefcase"
		"scaleImage"		"1"
		"if_mvm"
		{
			"xpos"		"61"
			"ypos"		"13"
			"wide"		"38"
			"tall"		"38"
		}
	}
	"StatusIcon"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"StatusIcon"
		"xpos"		"66"
		"ypos"		"18"
		"zpos"		"3"
		"wide"		"28"
		"tall"		"28"
		"visible"		"1"
		"enabled"		"1"
		"image"		"../hud/objectives_flagpanel_ico_flag_home"
		"scaleImage"		"1"
		"if_mvm"
		{
			"visible"		"0"
		}
	}
}
