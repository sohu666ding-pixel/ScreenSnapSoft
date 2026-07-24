from PIL import Image


def merge_to_pdf(image_paths, out_path):
    """把多张图片按顺序合并为单个 PDF（需求 7）。返回 out_path。"""
    if not image_paths:
        raise ValueError("没有可合并的图片")

    images = []
    try:
        for p in image_paths:
            images.append(Image.open(p).convert("RGB"))
        first, rest = images[0], images[1:]
        first.save(out_path, "PDF", save_all=True, append_images=rest)
    finally:
        for im in images:
            im.close()
    return out_path
