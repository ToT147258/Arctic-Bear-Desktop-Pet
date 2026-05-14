# 真实北极熊动画帧目录

这里放真正的北极熊逐帧动画素材。程序只会播放这里的 GIF/WebP/PNG 序列帧，不会再用单张图片伪装动作。

支持两种方式：

```text
real_actions/
├─ idle.gif
├─ wave.gif
├─ walk_right.gif
```

或：

```text
real_actions/
├─ idle/
│  ├─ idle_000.png
│  ├─ idle_001.png
│  └─ ...
├─ wave/
├─ walk_right/
├─ walk_left/
├─ jump/
├─ sleep/
└─ drag/
```

建议素材要求：

- 同一只北极熊，同一视角，同一尺寸。
- 背景已经透明。
- 每个动作至少 12 帧，24 帧以上会更顺滑。
- 帧尺寸建议 360x520 或等比例透明 PNG。
- `walk_left` 可以不提供，程序会从 `walk_right` 镜像生成。

如果只有视频，需要先用 Blender、ffmpeg、AE、剪映等工具导出透明 PNG 序列帧或 GIF 后再放进来。
