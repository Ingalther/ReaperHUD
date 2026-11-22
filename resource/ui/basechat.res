// The Reaper HUD - made by Ingalther. Licence: CC BY-NC-SA 4.0 (credit required, no selling).
"Resource/UI/BaseChat.res"
{
	"HudChat"
	{
		"ControlName"		"EditablePanel"
		"fieldName"		"HudChat"
		"visible"		"1"
		"enabled"		"1"
		"xpos"		"17"
		"ypos"		"225"
		"wide"		"300"
		"tall"		"112"
		"PaintBackgroundType"		"0"
		"bgcolor_override"		"9 9 11 225"
		"paintborder"		"0"
	}
	"ChatInputLine"
	{
		"ControlName"		"EditablePanel"
		"fieldName"		"ChatInputLine"
		"visible"		"1"
		"enabled"		"1"
		"xpos"		"10" [$WIN32]
		"xpos"		"42" [$X360]
		"ypos"		"395"
		"wide"		"260"
		"tall"		"2"
		"PaintBackgroundType"		"0"
		"bgcolor_override"		"0 0 0 0"
		"fgcolor_override"		"236 232 232 255"
	}
	"ChatFiltersButton"
	{
		"ControlName"		"Button"
		"fieldName"		"ChatFiltersButton"
		"xpos"		"225"
		"ypos"		"2"
		"wide"		"45"
		"tall"		"15"
		"autoResize"		"1"
		"pinCorner"		"0"
		"visible"		"1"
		"enabled"		"1"
		"tabPosition"		"0"
		"labelText"		"#chat_filterbutton"
		"textAlignment"		"center"
		"dulltext"		"0"
		"brighttext"		"0"
		"Default"		"0"
		"paintbackground"		"1"
		"defaultBgColor_override"		"16 16 18 235"
		"armedBgColor_override"		"160 18 34 255"
		"depressedBgColor_override"		"224 26 46 255"
		"defaultFgColor_override"		"236 232 232 255"
		"armedFgColor_override"		"255 255 255 255"
		"depressedFgColor_override"		"7 7 9 255"
		"paintborder"		"0"
	}
	"HudChatHistory"
	{
		"ControlName"		"RichText"
		"fieldName"		"HudChatHistory"
		"xpos"		"10" [$WIN32]
		"ypos"		"17" [$WIN32]
		"xpos"		"10" [$X360]
		"ypos"		"10" [$X360]
		"wide"		"260"
		"tall"		"75"
		"wrap"		"1"
		"autoResize"		"1"
		"pinCorner"		"1"
		"visible"		"1"
		"enabled"		"1"
		"labelText"		""
		"textAlignment"		"south-west"
		"font"		"RK_Chat"
		"maxchars"		"-1"
		"bgcolor_override"		"0 0 0 110"
		"fgcolor_override"		"236 232 232 255"
	}
}
