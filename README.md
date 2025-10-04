# MIDI-MCSTRUCTURE_NEXT

#### 介绍
MIDI音乐转为mcstructure或mcfunction。

### 特性
1. 支持新旧Java版和基岩版游戏，对各个版本做了语法和音效的适配
2. 支持加载标准.lrc文件或加载MIDI内嵌歌词以在游戏中显示
3. 支持在.mcstructure文件中预添加一些指令或结构
4. 支持压缩游戏指令条数等......

### 编辑指令
指令使用JSON格式存储在程序运行目录/Asset/text/profile.json中，可使用Windows自带的记事本或其他文本编辑器来编辑。
如果一切顺利，你应当看到以下的文件结构：

```
"new_bedrock": {
  "command": {
    "delay": "/execute...",
    "clock": [
      "/execute...",
      "/scoreboard...",
      "/scoreboard..."
    ],
    "address": [
      "/execute..",
      "/scoreboard...",
      "/scoreboard..."
    ],
    "lyrics": [
      "/titleraw...",
      "/titleraw...",
      "/titleraw..."
    ],
    "timer_target_selector": {
      "regular": "MMS_Service={VALUE}",
      "compressed": [
        "MMS_Service=!{VALUE}",
        "{START}..{END}",
        ","
      ]
    }
  }
```
根据游戏版本分为了新旧基岩版和Java版，分别对应new_bedrock/old_bedrock/new_java/old_java，改的时候需要注意版本。

一个版本中，又根据模式分为了命令链延迟、计分板时钟和时钟与编号，分别对应delay/clock/address；此外lyrics指歌词字幕的指令，timer_target_selector指用于计时的计分板选择器。

计分板时钟和时钟与编号模式支持在命令链最后追加若干条指令，除配置文件中对应模式的第一条指令，其他均为追加指令。

一条指令中，使用{SOUND}代表我的世界中的音效ID；  
{POSITION}代表音效播放位置（用于立体声效果）；  
{VOLUME}代表音量（范围0.0 ~ 1）；  
{PITCH}代表音调（会根据游戏版本自动限制）；  
{TIME}在追加指令中指时间全长，单位为一个游戏刻；  
另外，歌词字幕中{LAST}指上一条歌词，{REAL}指当前歌词，{NEXT}指下一条歌词。  