// The Reaper HUD - made by Ingalther. Licence: CC BY-NC-SA 4.0 (credit required, no selling).
"Resource/UI/HudObjectiveTimePanel.res"
{
	"TimePanelBG"
	{
		"ControlName"		"ScalableImagePanel"
		"fieldName"		"TimePanelBG"
		"xpos"		"16"
		"xpos_hidef"		"108"
		"xpos_lodef"		"108"
		"ypos"		"9"
		"zpos"		"2"
		"wide"		"0"
		"tall"		"0"
		"visible"		"1"
		"enabled"		"1"
		"image"		"../hud/objectives_timepanel_blue_bg"
		"scaleImage"		"1"
		"if_match"
		{
			"visible"		"0"
		}
	}
	"TimePanelProgressBar"
	{
		"ControlName"		"CTFProgressBar"
		"fieldName"		"TimePanelProgressBar"
		"xpos"		"67"
		"xpos_hidef"		"159"
		"xpos_lodef"		"165"
		"ypos"		"16"
		"ypos_hidef"		"15"
		"ypos_lodef"		"16"
		"zpos"		"4"
		"wide"		"0"
		"tall"		"0"
		"visible"		"1"
		"enabled"		"1"
		"scaleImage"		"1"
		"image"		"../hud/objectives_timepanel_progressbar"
		"color_active"		"TimerProgress.Active"
		"color_inactive"		"TimerProgress.InActive"
		"color_warning"		"TimerProgress.Warning"
		"percent_warning"		"0.75"
		"if_match"
		{
			"visible"		"0"
		}
	}
	"WaitingForPlayersLabel"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"WaitingForPlayersLabel"
		"xpos"		"0"
		"ypos"		"36"
		"zpos"		"5"
		"wide"		"f0"
		"tall"		"8"
		"visible"		"0"
		"enabled"		"1"
		"labelText"		"#game_WaitingForPlayers"
		"textAlignment"		"center"
		"dulltext"		"0"
		"brighttext"		"0"
		"wrap"		"0"
		"font"		"RK_StripLabel"
		"if_match"
		{
			"proportionaltoparent"		"1"
			"xpos"		"0"
			"ypos"		"36"
			"wide"		"f0"
			"font"		"RK_StripLabel"
		}
		"proportionaltoparent"		"1"
		"allcaps"		"1"
		"fgcolor"		"RK_Text"
	}
	"WaitingForPlayersBG"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"WaitingForPlayersBG"
		"xpos"		"16" [$WIN32]
		"xpos"		"11" [$X360]
		"ypos"		"31"
		"ypos_hidef"		"-100"
		"ypos_lodef"		"-100"
		"zpos"		"1"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_timepanel_suddendeath"
		"scaleImage"		"1"
		"if_match"
		{
			"wide"		"0"
		}
	}
	"OvertimeLabel"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"OvertimeLabel"
		"xpos"		"0"
		"ypos"		"36"
		"zpos"		"5"
		"wide"		"f0"
		"tall"		"8"
		"visible"		"0"
		"enabled"		"1"
		"labelText"		"#game_Overtime"
		"textAlignment"		"center"
		"dulltext"		"0"
		"brighttext"		"0"
		"wrap"		"0"
		"font"		"RK_StripLabel"
		"if_match"
		{
			"proportionaltoparent"		"1"
			"xpos"		"0"
			"ypos"		"36"
			"wide"		"f0"
			"font"		"RK_StripLabel"
		}
		"proportionaltoparent"		"1"
		"allcaps"		"1"
		"fgcolor"		"RK_Text"
	}
	"OvertimeBG"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"OvertimeBG"
		"xpos"		"16" [$WIN32]
		"xpos"		"11" [$X360]
		"ypos"		"31"
		"ypos_hidef"		"-100"
		"ypos_lodef"		"-100"
		"zpos"		"1"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_timepanel_suddendeath"
		"scaleImage"		"1"
		"if_match"
		{
			"wide"		"0"
		}
	}
	"SuddenDeathLabel"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"SuddenDeathLabel"
		"xpos"		"0"
		"ypos"		"36"
		"zpos"		"5"
		"wide"		"f0"
		"tall"		"8"
		"visible"		"0"
		"enabled"		"1"
		"labelText"		"#game_SuddenDeath"
		"textAlignment"		"center"
		"dulltext"		"0"
		"brighttext"		"0"
		"wrap"		"0"
		"font"		"RK_StripLabel"
		"if_match"
		{
			"proportionaltoparent"		"1"
			"xpos"		"0"
			"ypos"		"36"
			"wide"		"f0"
			"font"		"RK_StripLabel"
		}
		"proportionaltoparent"		"1"
		"allcaps"		"1"
		"fgcolor"		"RK_Text"
	}
	"SuddenDeathBG"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"SuddenDeathBG"
		"xpos"		"16" [$WIN32]
		"xpos"		"11" [$X360]
		"ypos"		"31"
		"ypos_hidef"		"-100"
		"ypos_lodef"		"-100"
		"zpos"		"1"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_timepanel_suddendeath"
		"scaleImage"		"1"
		"if_match"
		{
			"wide"		"0"
		}
	}
	"SetupLabel"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"SetupLabel"
		"xpos"		"0"
		"ypos"		"36"
		"zpos"		"5"
		"wide"		"f0"
		"tall"		"8"
		"visible"		"0"
		"enabled"		"1"
		"labelText"		"#game_Setup"
		"textAlignment"		"center"
		"dulltext"		"0"
		"brighttext"		"0"
		"wrap"		"0"
		"font"		"RK_StripLabel"
		"if_match"
		{
			"proportionaltoparent"		"1"
			"xpos"		"0"
			"ypos"		"36"
			"wide"		"f0"
			"font"		"RK_StripLabel"
		}
		"proportionaltoparent"		"1"
		"allcaps"		"1"
		"fgcolor"		"RK_Text"
	}
	"SetupBG"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"SetupBG"
		"xpos"		"16" [$WIN32]
		"xpos"		"11" [$X360]
		"ypos"		"31"
		"ypos_hidef"		"-100"
		"ypos_lodef"		"-100"
		"zpos"		"1"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_timepanel_suddendeath"
		"scaleImage"		"1"
		"if_match"
		{
			"wide"		"0"
		}
	}
	"ServerTimeLimitLabel"
	{
		"ControlName"		"CExLabel"
		"fieldName"		"ServerTimeLimitLabel"
		"xpos"		"0"
		"ypos"		"36"
		"zpos"		"5"
		"wide"		"f0"
		"tall"		"8"
		"visible"		"0"
		"enabled"		"1"
		"labelText"		"%servertimeleft%"
		"textAlignment"		"center"
		"dulltext"		"0"
		"brighttext"		"0"
		"wrap"		"0"
		"font"		"RK_StripLabel"
		"if_match"
		{
			"proportionaltoparent"		"1"
			"xpos"		"0"
			"ypos"		"36"
			"wide"		"f0"
			"font"		"RK_StripLabel"
		}
		"proportionaltoparent"		"1"
		"allcaps"		"1"
		"fgcolor"		"RK_Text"
	}
	"ServerTimeLimitLabelBG"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"ServerTimeLimitLabelBG"
		"xpos"		"16" [$WIN32]
		"xpos"		"11" [$X360]
		"ypos"		"31"
		"ypos_hidef"		"-100"
		"ypos_lodef"		"-100"
		"zpos"		"1"
		"wide"		"0"
		"tall"		"0"
		"visible"		"0"
		"enabled"		"1"
		"image"		"../hud/objectives_timepanel_suddendeath"
		"scaleImage"		"1"
		"if_match"
		{
			"wide"		"0"
		}
	}
	"RK_TimerBG"
	{
		"ControlName"		"CTFImagePanel"
		"fieldName"		"RK_TimerBG"
		"xpos"		"cs-0.5"
		"ypos"		"0"
		"zpos"		"1"
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
	}
}
