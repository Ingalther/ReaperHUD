// The Reaper HUD - made by Ingalther. Licence: CC BY-NC-SA 4.0 (credit required, no selling).
"Resource/UI/HudObjectiveFlagPanel.res"
{
	"ObjectiveStatusFlagPanel"
	{
		"ControlName"		"EditablePanel"
		"fieldName"		"ObjectiveStatusFlagPanel"
		"xpos"		"0"
		"ypos"		"0"
		"zpos"		"1"
		"wide"		"f0"
		"tall"		"480"
		"visible"		"1"
		"enabled"		"1"
		"if_hybrid"
		{
			"zpos"		"-1"
		}
	}
	"LeftSideBG"
	{
		"ControlName"		"ImagePanel"
		"fieldName"		"LeftSideBG"
		"xpos"		"c-140"
		"ypos"		"r75" [$WIN32]
		"ypos"		"r96" [$X360]
		"zpos"		"1"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_flagpanel_bg_left"
		"scaleImage"		"1"
		"if_hybrid"
		{
			"visible"		"0"
		}
		"if_mvm"
		{
			"visible"		"0"
		}
		"if_specialdelivery"
		{
			"visible"		"0"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
	}
	"RightSideBG"
	{
		"ControlName"		"ImagePanel"
		"fieldName"		"RightSideBG"
		"xpos"		"c-140"
		"ypos"		"r75" [$WIN32]
		"ypos"		"r96" [$X360]
		"zpos"		"1"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_flagpanel_bg_right"
		"scaleImage"		"1"
		"if_hybrid"
		{
			"visible"		"0"
		}
		"if_mvm"
		{
			"visible"		"0"
		}
		"if_specialdelivery"
		{
			"visible"		"0"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
	}
	"OutlineBG"
	{
		"ControlName"		"ImagePanel"
		"fieldName"		"OutlineBG"
		"xpos"		"c-140"
		"ypos"		"r75" [$WIN32]
		"ypos"		"r96" [$X360]
		"zpos"		"2"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_flagpanel_bg_outline"
		"scaleImage"		"1"
		"if_hybrid"
		{
			"visible"		"0"
		}
		"if_mvm"
		{
			"visible"		"0"
		}
		"if_specialdelivery"
		{
			"visible"		"0"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
	}
	"BlueScore"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"BlueScore"
		"xpos"		"c-27"
		"ypos"		"4"
		"zpos"		"5"
		"wide"		"14"
		"tall"		"16"
		"visible"		"1"
		"enabled"		"1"
		"textAlignment"		"west"
		"labelText"		"%bluescore%"
		"font"		"RK_TopScore"
		"fgcolor"		"128 178 255 255"
		"if_hybrid"
		{
			"visible"		"0"
		}
		"if_mvm"
		{
			"visible"		"0"
		}
		"if_specialdelivery"
		{
			"visible"		"0"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
	}
	"BlueScoreShadow"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"BlueScoreShadow"
		"xpos"		"0"
		"ypos"		"0"
		"zpos"		"7"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"textAlignment"		"west"
		"labelText"		"%bluescore%"
		"font"		"HudFontBig"
		"font_hidef"		"HudFontGiant"
		"font_lodef"		"HudFontGiant"
		"fgcolor"		"Black"
		"if_hybrid"
		{
			"visible"		"0"
		}
		"if_mvm"
		{
			"visible"		"0"
		}
		"if_specialdelivery"
		{
			"visible"		"0"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
	}
	"RedScore"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"RedScore"
		"xpos"		"c13"
		"ypos"		"4"
		"zpos"		"5"
		"wide"		"14"
		"tall"		"16"
		"visible"		"1"
		"enabled"		"1"
		"textAlignment"		"east"
		"labelText"		"%redscore%"
		"font"		"RK_TopScore"
		"fgcolor"		"255 92 104 255"
		"if_hybrid"
		{
			"visible"		"0"
		}
		"if_mvm"
		{
			"visible"		"0"
		}
		"if_specialdelivery"
		{
			"visible"		"0"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
	}
	"RedScoreShadow"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"RedScoreShadow"
		"xpos"		"0"
		"ypos"		"0"
		"zpos"		"7"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"textAlignment"		"east"
		"labelText"		"%redscore%"
		"font"		"HudFontBig"
		"font_hidef"		"HudFontGiant"
		"font_lodef"		"HudFontGiant"
		"fgcolor"		"Black"
		"if_hybrid"
		{
			"visible"		"0"
		}
		"if_mvm"
		{
			"visible"		"0"
		}
		"if_specialdelivery"
		{
			"visible"		"0"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
	}
	"OutlineImage"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"OutlineImage"
		"xpos"		"c-50"
		"ypos"		"r127" [$WIN32]
		"ypos"		"r148" [$X360]
		"zpos"		"9"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"image"		"replay/thumbnails/rk/blank"
		"scaleImage"		"1"
	}
	"CarriedImage"
	{
		"ControlName"		"ImagePanel"
		"fieldName"		"CarriedImage"
		"xpos"		"c-12"
		"ypos"		"r41"
		"zpos"		"10"
		"wide"		"24"
		"tall"		"24"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_flagpanel_carried_red"
		"scaleImage"		"1"
		"drawcolor"		"0 0 0 0"
		"border"		"RK_IntelCard"
		"paintborder"		"1"
	}
	"PlayingTo"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"PlayingTo"
		"xpos"		"c-55"
		"ypos"		"27"
		"zpos"		"5"
		"wide"		"110"
		"tall"		"8"
		"visible"		"1"
		"enabled"		"1"
		"labelText"		"#TF_PlayingTo"
		"textAlignment"		"center"
		"dulltext"		"0"
		"brighttext"		"0"
		"font"		"RK_StripLabel"
		"fgcolor"		"RK_Text"
		"if_hybrid"
		{
			"visible"		"0"
		}
		"if_mvm"
		{
			"visible"		"0"
		}
		"if_specialdelivery"
		{
			"visible"		"0"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
		"allcaps"		"1"
	}
	"PlayingToBG"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"PlayingToBG"
		"xpos"		"c-75" [$WIN32]
		"xpos"		"c-70" [$X360]
		"ypos"		"r31" [$WIN32]
		"ypos"		"r51" [$X360]
		"zpos"		"3"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_flagpanel_bg_playingto"
		"image_hidef"		"../hud/objectives_flagpanel_bg_playingto_hidef"
		"scaleImage"		"1"
		"if_hybrid"
		{
			"visible"		"0"
		}
		"if_mvm"
		{
			"visible"		"0"
		}
		"if_specialdelivery"
		{
			"visible"		"0"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
	}
	"BlueFlag"
	{
		"ControlName"		"CTFFlagStatus"
		"fieldName"		"BlueFlag"
		"xpos"		"c-160"
		"ypos"		"r62"
		"zpos"		"5"
		"wide"		"160"
		"tall"		"90"
		"visible"		"1"
		"enabled"		"1"
		"if_hybrid"
		{
			"visible"		"0"
			"ypos"		"r100"
		}
		"if_hybrid_single"
		{
			"xpos"		"c-80"
		}
		"if_hybrid_double"
		{
			"xpos"		"c-115"
		}
		"if_specialdelivery"
		{
			"ypos"		"r100"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
	}
	"RedFlag"
	{
		"ControlName"		"CTFFlagStatus"
		"fieldName"		"RedFlag"
		"xpos"		"c0"
		"ypos"		"r62"
		"zpos"		"5"
		"wide"		"160"
		"tall"		"90"
		"visible"		"1"
		"enabled"		"1"
		"if_hybrid"
		{
			"visible"		"0"
			"ypos"		"r100"
		}
		"if_hybrid_single"
		{
			"xpos"		"c-80"
		}
		"if_hybrid_double"
		{
			"xpos"		"c-45"
		}
		"if_specialdelivery"
		{
			"ypos"		"r100"
		}
		"if_no_flags"
		{
			"visible"		"0"
		}
	}
	"CaptureFlag"
	{
		"ControlName"		"CTFArrowPanel"
		"fieldName"		"CaptureFlag"
		"xpos"		"c-20"
		"ypos"		"r49"
		"zpos"		"5"
		"wide"		"40"
		"tall"		"40"
		"visible"		"0"
		"enabled"		"1"
	}
	"PoisonIcon"
	{
		"ControlName"		"ImagePanel"
		"fieldName"		"PoisonIcon"
		"xpos"		"cs-0.5"
		"ypos"		"r75"
		"zpos"		"6"
		"wide"		"40"
		"tall"		"o1"
		"visible"		"0"
		"enabled"		"1"
		"image"		"marked_for_death"
		"scaleImage"		"1"
	}
	"PoisonTimeLabel"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"PoisonTimeLabel"
		"xpos"		"cs-0.5"
		"ypos"		"r65"
		"zpos"		"6"
		"wide"		"40"
		"tall"		"20"
		"visible"		"0"
		"enabled"		"1"
		"textAlignment"		"center"
		"labelText"		"%redscore%"
		"font"		"HudFontMediumBold"
		"fgcolor"		"TanLight"
	}
	"SpecCarriedImage"
	{
		"ControlName"		"ImagePanel"
		"fieldName"		"SpecCarriedImage"
		"xpos"		"c-12"
		"ypos"		"r41"
		"zpos"		"10"
		"wide"		"24"
		"tall"		"24"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_flagpanel_carried_red"
		"scaleImage"		"1"
		"drawcolor"		"0 0 0 0"
		"border"		"RK_IntelCard"
		"paintborder"		"1"
	}
	"RK_FlagBox"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"RK_FlagBox"
		"xpos"		"cs-0.5"
		"ypos"		"0"
		"zpos"		"0"
		"wide"		"59"
		"tall"		"26"
		"visible"		"1"
		"enabled"		"1"
		"scaleImage"		"1"
		"image"		"replay/thumbnails/rk/ig_timer"
		"mouseinputenabled"		"0"
		"proportionaltoparent"		"1"
		"teambg_1"		"replay/thumbnails/rk/ig_timer"
		"teambg_2"		"replay/thumbnails/rk/ig_timer"
		"teambg_3"		"replay/thumbnails/rk/b/ig_timer"
		"if_mvm"
		{
			"visible"		"0"
		}
	}
}
