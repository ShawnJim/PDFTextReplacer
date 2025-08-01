#!/usr/bin/env python3
"""
PDF文本替换脚本 - PyMuPDF优化版（最终兼容版）
使用PyMuPDF的精确文本定位和替换功能，保留原始字体和样式，并支持加载本地字体。
"""

import sys
import os
import time
import argparse
from typing import Dict, List, Tuple
import logging
import fitz  # PyMuPDF
import tempfile
import shutil

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PyMuPDFTextReplacer:
    """使用PyMuPDF的文本替换器"""

    def __init__(self, rules_source: str | Dict[str, str]):
        """
        初始化替换器

        Args:
            rules_source: 替换规则，可以是文件路径(str)或规则字典(dict)
        """
        if isinstance(rules_source, dict):
            self.rules = rules_source
            logger.info(f"从字典加载了 {len(self.rules)} 条替换规则")
        else:
            self.rules = self._load_rules_from_file(rules_source)
            logger.info(f"从文件 {rules_source} 加载了 {len(self.rules)} 条替换规则")

        # 定义并创建字体目录
        self.fonts_dir = "fonts"
        if not os.path.exists(self.fonts_dir):
            os.makedirs(self.fonts_dir)
            logger.info(f"创建字体目录: {self.fonts_dir}")

    def _load_rules_from_file(self, rules_file: str) -> Dict[str, str]:
        """
        从文件加载替换规则

        Args:
            rules_file: 规则文件路径

        Returns:
            替换规则字典 {原文本: 替换文本}
        """
        rules = {}
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('|')
                    if len(parts) != 2:
                        logger.warning(f"第 {line_num} 行格式错误，跳过: {line}")
                        continue
                    rules[parts[0].strip()] = parts[1].strip()
        except Exception as e:
            logger.error(f"读取规则文件失败: {e}")
            raise
        return rules

    def replace_pdf(self, input_pdf: str, output_pdf: str, method: str = 'precise'):
        """
        执行PDF文本替换

        Args:
            input_pdf: 输入PDF文件路径
            output_pdf: 输出PDF文件路径
            method: 替换方法 ('precise', 'overlay', 'hybrid')
        """
        start_time = time.time()
        try:
            if method == 'precise':
                total_replacements = self._precise_replace_fixed(input_pdf, output_pdf)
            elif method == 'overlay':
                total_replacements = self._overlay_replace(input_pdf, output_pdf)
            elif method == 'hybrid':
                total_replacements = self._hybrid_replace(input_pdf, output_pdf)
            else:
                logger.error(f"未知的替换方法: {method}")
                return

            elapsed_time = time.time() - start_time
            logger.info(f"处理完成！")
            logger.info(f"总计替换: {total_replacements} 处")
            logger.info(f"耗时: {elapsed_time:.2f} 秒")
            logger.info(f"输出文件: {output_pdf}")

        except Exception as e:
            logger.error(f"处理PDF时出错: {e}")
            raise

    def _find_local_font(self, font_name: str) -> str | None:
        """在本地fonts文件夹中查找字体文件"""
        for ext in ['.ttf', '.otf', '.ttc']:
            for f in os.listdir(self.fonts_dir):
                if f.lower().startswith(font_name.lower()) and f.lower().endswith(ext):
                    return os.path.join(self.fonts_dir, f)
        return None

    def _precise_replace_fixed(self, input_pdf: str, output_pdf: str) -> int:
        """
        修复版精确替换方法：采用“查找-擦除-写入”三步法，并精确对齐基线。
        """
        logger.info("使用修复版精确替换方法...")
        total_replacements = 0
        BUILTIN_FONTS = ["helv", "cour", "timo", "symb", "zadb", "times", "courier", "helvetica", "symbol",
                         "zapfdingbats"]

        doc = fitz.open(input_pdf)
        logger.info(f"打开PDF文件成功，共 {len(doc)} 页")

        for page_num, page in enumerate(doc):

            # 1. 查找：收集所有需要替换的动作和位置信息
            actions = []
            for old_text, new_text in self.rules.items():
                text_instances = page.search_for(old_text)
                for inst in text_instances:
                    text_dict = page.get_text("dict", clip=inst)
                    fontname, fontsize, text_color = "helv", 12, (0, 0, 0)
                    # 核心改动：默认基线为矩形框底部，但会尝试寻找更精确的
                    baseline = inst.y1

                    # 提取字体样式和精确基线
                    for block in text_dict["blocks"]:
                        if block["type"] == 0:
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    if old_text in span["text"]:
                                        fontname = span.get("font", "helv").split("+")[-1]
                                        fontsize = span.get("size", 12)
                                        baseline = span.get("origin")[1]  # 获取精确基线Y坐标
                                        color = span.get("color", 0)
                                        if isinstance(color, int):
                                            text_color = (((color >> 16) & 0xFF) / 255.0, ((color >> 8) & 0xFF) / 255.0,
                                                          (color & 0xFF) / 255.0)
                                        break

                    actions.append({
                        "rect": inst, "new_text": new_text, "fontname": fontname,
                        "fontsize": fontsize, "color": text_color, "baseline": baseline
                    })

            if not actions:
                continue

            # 2. 擦除：将所有找到的旧文本区域标记为空白并应用
            for action in actions:
                page.add_redact_annot(action["rect"], text="")

            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            # 3. 写入：在擦除后的空白区域写入新文本
            for action in actions:
                font_to_use = action["fontname"]
                font_file_path = None

                # 检查是否是自定义字体并查找文件
                is_custom_font = font_to_use.lower().split("-")[0] not in BUILTIN_FONTS
                if is_custom_font:
                    font_file_path = self._find_local_font(font_to_use)
                    if not font_file_path:
                        logger.warning(f"警告: 字体 '{font_to_use}' 未找到，将使用 'helv' 替换。")
                        font_to_use = "helv"

                try:
                    # 对于自定义字体，需要先将其注册到页面
                    if font_file_path:
                        page.insert_font(fontfile=font_file_path, fontname=font_to_use)

                    # 核心改动：使用精确的插入点 (rect.x0, baseline)
                    insertion_point = fitz.Point(action["rect"].x0, action["baseline"])
                    page.insert_text(insertion_point,
                                     action["new_text"],
                                     fontname=font_to_use,
                                     fontsize=action["fontsize"],
                                     color=action["color"])
                except Exception as e:
                    logger.error(f"写入文本 '{action['new_text']}' 失败: {e}")

            total_replacements += len(actions)
            logger.info(f"页面 {page_num + 1}: 完成 {len(actions)} 处替换")

        doc.save(output_pdf, garbage=4, deflate=True, clean=True)
        doc.close()
        return total_replacements

    def _overlay_replace(self, input_pdf: str, output_pdf: str) -> int:
        """
        覆盖替换方法：使用白色矩形覆盖原文本，然后插入新文本
        """
        logger.info("使用覆盖替换方法...")
        total_replacements = 0
        shutil.copy2(input_pdf, output_pdf)
        doc = fitz.open(output_pdf)

        for page_num, page in enumerate(doc):
            page_replacements = 0
            replacements = []

            for old_text, new_text in self.rules.items():
                text_instances = page.search_for(old_text)
                for inst in text_instances:
                    text_dict = page.get_text("dict", clip=inst)
                    font_info = {'fontname': 'helv', 'fontsize': 12, 'color': (0, 0, 0), 'baseline': inst.y1}
                    for block in text_dict["blocks"]:
                        if block["type"] == 0:
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    if old_text in span["text"]:
                                        font_info['fontname'] = span.get("font", "helv").split("+")[-1]
                                        font_info['fontsize'] = span.get("size", 12)
                                        font_info['baseline'] = span.get("origin")[1]
                                        color = span.get("color", 0)
                                        if isinstance(color, int):
                                            font_info['color'] = (((color >> 16) & 0xFF) / 255.0,
                                                                  ((color >> 8) & 0xFF) / 255.0, (color & 0xFF) / 255.0)
                                        break
                    replacements.append({'rect': inst, 'new_text': new_text, 'font_info': font_info})

            if replacements:
                replacements.sort(key=lambda x: (x['rect'].y0, x['rect'].x0), reverse=True)
                for repl in replacements:
                    rect = fitz.Rect(repl['rect'])
                    font_info = repl['font_info']
                    shape = page.new_shape()
                    shape.draw_rect(rect)
                    shape.finish(color=(1, 1, 1), fill=(1, 1, 1), width=0)
                    shape.commit()
                    insert_point = fitz.Point(rect.x0, font_info['baseline'])
                    try:
                        rc = page.insert_text(insert_point, repl['new_text'], fontname=font_info['fontname'],
                                              fontsize=font_info['fontsize'], color=font_info['color'])
                        if rc < 0: raise Exception("插入失败")
                    except:
                        logger.debug(f"使用原始字体 {font_info['fontname']} 失败，使用标准字体")
                        page.insert_text(insert_point, repl['new_text'], fontsize=font_info['fontsize'],
                                         color=font_info['color'])
                    page_replacements += 1

            if page_replacements > 0:
                total_replacements += page_replacements
                logger.info(f"页面 {page_num + 1}: 完成 {page_replacements} 处替换")

        doc.save(output_pdf, incremental=False, garbage=4, deflate=True)
        doc.close()
        return total_replacements

    def _hybrid_replace(self, input_pdf: str, output_pdf: str) -> int:
        """
        混合方法：先尝试精确替换，失败则使用覆盖方法
        """
        logger.info("使用混合替换方法...")
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            replacements = self._precise_replace_fixed(input_pdf, tmp_path)
            if self._verify_replacements(tmp_path):
                shutil.move(tmp_path, output_pdf)
                return replacements
            else:
                logger.warning("精确替换未完全成功，使用覆盖方法")
                os.remove(tmp_path)
                return self._overlay_replace(input_pdf, output_pdf)
        except Exception as e:
            logger.error(f"混合替换失败: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def _verify_replacements(self, pdf_path: str) -> bool:
        """快速验证替换是否成功"""
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                for old_text in self.rules.keys():
                    if page.search_for(old_text):
                        doc.close()
                        return False
            doc.close()
            return True
        except:
            return False


def verify_replacements(pdf_path: str, rules: Dict[str, str]):
    """验证替换结果"""
    logger.info("\n验证替换结果...")
    doc = fitz.open(pdf_path)
    success_count, failed_rules = 0, []

    for old_text, new_text in rules.items():
        found_old, found_new = False, False
        for page in doc:
            if page.search_for(old_text): found_old = True
            if page.search_for(new_text): found_new = True
        if found_new and not found_old:
            success_count += 1
            logger.info(f"✓ 成功替换: {old_text} -> {new_text}")
        elif found_old:
            failed_rules.append(old_text)
            logger.warning(f"✗ 未替换: {old_text} (仍然存在)")
        else:
            logger.info(f"- 未找到: {old_text} (原文本不存在)")
    doc.close()
    logger.info(f"\n验证完成: {success_count}/{len(rules)} 规则成功")
    return failed_rules


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='PDF文本替换工具（PyMuPDF修复版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
替换方法说明:
  precise - 精确替换（推荐）：使用标记功能，保持原始字体，并支持从'fonts'目录加载本地字体。
  overlay - 覆盖替换：白色覆盖+重新插入，更可靠但可能有细微差异。
  hybrid  - 混合替换：自动选择最佳方法。

示例:
  python pdf_replacer_pymupdf.py input.pdf output.pdf rules.txt
  python pdf_replacer_pymupdf.py input.pdf output.pdf rules.txt --method overlay
  python pdf_replacer_pymupdf.py input.pdf output.pdf rules.txt --verify
        """
    )
    parser.add_argument('input_pdf', help='输入PDF文件路径')
    parser.add_argument('output_pdf', help='输出PDF文件路径')
    parser.add_argument('rules_file', help='替换规则文件路径')
    parser.add_argument('--method', choices=['precise', 'overlay', 'hybrid'], default='precise',
                        help='替换方法（默认: precise）')
    parser.add_argument('--verify', action='store_true', help='验证替换结果')
    args = parser.parse_args()

    if not os.path.exists(args.input_pdf):
        logger.error(f"输入文件不存在: {args.input_pdf}")
        sys.exit(1)
    if not os.path.exists(args.rules_file):
        logger.error(f"规则文件不存在: {args.rules_file}")
        sys.exit(1)
    if os.path.abspath(args.input_pdf) == os.path.abspath(args.output_pdf):
        logger.error("输出文件不能与输入文件相同！")
        sys.exit(1)

    try:
        replacer = PyMuPDFTextReplacer(args.rules_file)
        replacer.replace_pdf(args.input_pdf, args.output_pdf, method=args.method)
        if args.verify:
            failed_rules = verify_replacements(args.output_pdf, replacer.rules)
            if failed_rules:
                logger.warning(f"\n有 {len(failed_rules)} 条规则未成功替换")
                logger.info("建议尝试 --method overlay 或 --method hybrid")
    except Exception as e:
        logger.error(f"处理失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()