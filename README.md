# About QuakeMapFlipper 

I've been dabling with vibecoding Quake 1 related things. I hope to eventually get a random map generator going as well as major mods to the QuakeC and maybe later the engine itself.

After spending multiple hours fighting with ChatGPT trying to make a quake.map axis flipper, I got something that mostly worked. But, moving brushes like doors and lifts did not move correctly. As a result, it wasn't really playable. Some texture alignment issues were obvious as well. Additional prompts never resolved the issue and often caused new bugs. So, I gave up waiting for improvements with AI.

A few months later, I decided to give it another go with Gemini 2.5. 
Not having much hope and fully expecting a repeat of the ChatGPT issues, I gave it a simple prompt. It responded with a script I still haven't tried. I gave some clarifiactions reminding it about moving the entities and changing the targets of moving brushes. It spit out another script. I reminded it that texture alignment and a few other things also needed adjusted. It gave another script that I finally tested.

It seemed to work perfect the first try.
I tested it using the Quake 1 E1M1, E1M2, and DM1. I did not compile maps beyond that. If you do, please report back!

# Useage

run the python script as you would any other. (python is obviously required)
Pops up with a GUI. It asks for an input file, output file, and has check boxes for which axis you want to flip. Z makes it upside down, which is generally unplayable. 

# License

Like a lot of early quake stuff, I'll say:
This is free to do with as you please. Just don't claim it as your own. Attribution would be appreciated but is not required.

Please respect the licenses of any maps you use this on and give proper credit where credit is due. But, that is between you and the map maker. Not responsible for user actions.
