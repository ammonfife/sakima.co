---
name: ltx-video-1.0.0
description: Generate videos from images with the Lightricks LTX-2 model and document the required local runtime setup.
---

# LTX-2 Video Generation

Generate videos from images using Lightricks LTX-2 diffusion model.

## Requirements

```bash
pip install -U diffusers transformers accelerate
```

## Usage

```python
import torch
from diffusers import DiffusionPipeline
from diffusers.utils import load_image, export_to_video

# Device selection
# - "cuda" for NVIDIA GPUs
# - "mps" for Apple Silicon
device = "mps"  # or "cuda"

pipe = DiffusionPipeline.from_pretrained(
    "Lightricks/LTX-2",
    dtype=torch.bfloat16,
    device_map=device
)
pipe.to(device)

prompt = "A man with short gray hair plays a red electric guitar."
image = load_image(
    "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/guitar-man.png"
)

output = pipe(image=image, prompt=prompt).frames[0]
export_to_video(output, "output.mp4")
```

## Parameters

- `image`: Input image (PIL Image or URL via `load_image`)
- `prompt`: Text description of desired motion/action
- `frames[0]`: First batch of generated frames

## Output

Exports MP4 video file.

## Model Info

- **Model**: Lightricks/LTX-2
- **Source**: https://huggingface.co/Lightricks/LTX-2
- **Type**: Image-to-video diffusion
