Inspiration
-----------

There's a category of games characterized by:
- [Persistent](https://en.wikipedia.org/wiki/Persistent_world) MMO "strategy" and/or RPG
- Zero or disposable plot
- Free-to-play microtransaction-heavy, often "free to wait, pay to accelerate"
- Released on web game portals such as [Kongregate](www.kongregate.com)
- Often Korean or Chinese in providence with poor translation
- Title is often some combination of *Age|Call|Heroes|Legend|Knights* of *Destiny|Gods|War*
- There's a weird
  [disproportionate](http://img3.mmo.mmo4arab.com/news/2014/09/15/revelation1.jpg)
  boob
  [fixation](http://www.mmojam.com/wp-content/uploads/2014/12/Age-of-Civilization-The-Dawn-of-Civilization-Wallpaper.jpg)

There are
[many, many, many examples](https://www.kongregate.com/mmo-games), and they're generally terrible (but I play them for
the badges because I have a problem). I'm about 60% certain that the one I'm thinking of is
[Call of Gods](https://www.kongregate.com/games/callofgods/call-of-gods).
This game has a feature where other players can pillage your castle. I generally hate other online gamers, so I wanted
to calculate how to screw them in the most passive-aggressive and nerdy way possible.

Using [Octave](https://www.gnu.org/software/octave)'s
[linear programming solver](https://octave.org/doc/v4.0.0/Linear-Programming.html) I was able to calculate exactly how
many troops of each variety to produce such that they maximally consumed my various resources before I logged out. I
left my castle undefended, and so all attackers automatically won the siege and were able to pillage... nothing.

Block'Hood
----------

Fast-forward to 2018, and a very different game calls for somewhat similar analysis.
[Block'Hood](https://www.plethora-project.com/blockhood) is a city-builder focusing on ecological sustainability,
healthy community participation and conscientious resource generation/consumption. There's a particularly nefarious
challenge, the
[Zero Footprint Challenge](https://blockhood.gamepedia.com/Challenges#12._Zero_footprint),
wherein the player has to generate one resource (fresh air) without an excess in any other resource. Linear programming
is well-suited to such a task.

Enter this project. Since this is a hacky side-project, my language of choice is [Python](https://www.python.org) 3.
It's terse and has tonnes of third-party libraries.

Data Acquisition
----------------

To analyse this economy, the application needs a complete representation of all buildings and what they produce and
consume at what rates. To do this, I'm pulling from the community-maintained
[wiki](https://blockhood.gamepedia.com).

The pulling itself, as always, uses [requests](http://docs.python-requests.org).

For parsing, first I was using [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup), but then discovered that
I'm in luck: GamePedia uses MediaWiki and exposes a
[nice, RESTful JSON API](https://www.mediawiki.org/wiki/API:Main_page). Form a sane request, write a pagination loop,
and bam - we get the data we need.

But there's a problem. Many of the pages are
[stubs](https://blockhood.gamepedia.com/Category:Stubs) and don't have the data we need. I'm too lazy to update them by
hand, so I
[asked the developer for some data](https://www.facebook.com/blockhoodgame/posts/1877621299022835)
but haven't heard back.

Second approach: scrape the game itself. Based on a dumb directory search, the data most likely live in this file:

    SteamLibrary\steamapps\common\Blockhood\BLOCKHOOD v0_40_08_Data\sharedassets2.assets

This file is a [Unity](https://unity3d.com) assets bundle. To decode it we could use the apparently undocumented tool

    Unity\Editor\Data\Tools\binary2text.exe

Its usage blurb merely states:

    Usage: binary2text inputbinaryfile [outputtextfile] [-detailed]

To my "delight", the most recent version of Unity cannot parse this bundle, so apparently it's not whatsoever
backwards-compatible:

    Invalid serialized file version. File: "SteamLibrary\steamapps\common\Blockhood\BLOCKHOOD v0_40_08_Data\sharedassets2.assets".
    Expected version: 2018.2.3f1. Actual version: 5.6.2f1.

Using the tool from the older Unity 5.6.2 gets farther, producing:

    External References
    path(1): "globalgamemanagers.assets" GUID: 00000000000000000000000000000000 Type: 0
    path(2): "resources/unity_builtin_extra" GUID: 0000000000000000f000000000000000 Type: 0
    path(3): "library/unity default resources" GUID: 0000000000000000e000000000000000 Type: 0
    path(4): "resources.assets" GUID: 00000000000000000000000000000000 Type: 0
    path(5): "sharedassets0.assets" GUID: 00000000000000000000000000000000 Type: 0
    path(6): "sharedassets1.assets" GUID: 00000000000000000000000000000000 Type: 0
    
    Object #0 (ClassID: 150) at byte 439904 without type tree
    Object #1 (ClassID: 21) at byte 447608 without type tree
    Object #2 (ClassID: 21) at byte 448704 without type tree
    Object #3 (ClassID: 21) at byte 449800 without type tree
    Object #4 (ClassID: 21) at byte 449992 without type tree
    ...

Still useless.

Using the somewhat-sketchy-looking and unhelpfully closed-source
[UABE](https://github.com/DerPopo/UABE),
 it apparently successfully decodes the .assets bundle. In the list it presents, we ignore graphics and audio items, and
 find these:

    Name:    MonoBehaviour blockDB_current
    Type:    MonoBehaviour: BlockDatabase (Assembly-CSharp.dll)
    File ID: 0
    Path ID: 21228
    Size:    803924 bytes

    Name:    MonoBehaviour resourceDB
    Type:    MonoBehaviour: ResourceDatabase (Assembly-CSharp.dll)
    File ID: 0
    Path ID: 21231
    Size:    73240 bytes

Do a binary export of that file and it gets us something that appears to be a 32-bit-aligned serialized C# object. The
strings are UTF-8-encoded, which is particularly important for the text in international languages.

The type assembly can be loaded in [DotPeek](https://www.jetbrains.com/decompiler). The class of interest is:

    // Type: BlockDatabase
    // Assembly: Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null
    // MVID: 9389A4AF-DACD-4250-864C-FFB1C86AE6D0
    // Assembly location: SteamLibrary\steamapps\common\Blockhood\BLOCKHOOD v0_40_08_Data\Managed\Assembly-CSharp.dll

- The assembly uses .NET 3.5 on runtime 2.0.50727/MSIL.
- The assembly can be dynamically loaded or statically referenced
- If you try to statically reference it outside of Unity and then deserialize the class, you get
  [`ECall methods must be packaged into a system module`](https://forum.unity.com/threads/c-error-ecall-methods-must-be-packaged-into-a-system-module.199361/)
- If you try to load it into a Unity project, there are conflict problems because the assemblies are named identically 
  and Unity uses global objects with no namespace
- The `BlockDatabase` class is marked `[Serializable]` 
- The class parent `ScriptableObject` is marked `[StructLayout(LayoutKind.Sequential)]`
- The class cannot be deserialized via
  [`Marshal.PtrToStructure`](https://msdn.microsoft.com/en-us/library/4ca6d5z7(v=vs.110).aspx)
  because it contains generic `List<>`
- The class cannot be deserialized via
  [`BinaryFormatter`](https://msdn.microsoft.com/en-us/library/system.runtime.serialization.formatters.binary.binaryformatter(v=vs.110).aspx)
  because the database dump does not use that format
- The Unity deserialization code is probably in an unmanaged assembly to which this assembly refers using `extern`

Looking at the binary database dump file in a hex editor, it's fairly easy to line up the binary fields with those
shown in the decompiled model class. The integers and floats are in standard IEEE format, and the strings are
non-terminated and preceded by length.

Analysis
--------

Then, it does some caching and data munging, for eventual processing by
[Numpy](http://www.numpy.org)/[Scipy](https://scipy.org).
The eventual goal is to apply a
[Dantzig linear programming solver](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html)
to explore some optimal consumption patterns.