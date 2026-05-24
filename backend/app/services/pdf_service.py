"""PDF rendering service – LaTeX/Jinja2 to PDF with pdflatex fallback."""

import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Output directory for generated PDFs
PDF_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "pdfs"
PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Jinja2 environment for LaTeX templates
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    # Use different delimiters to avoid conflicts with LaTeX
    block_start_string="\\BLOCK{",
    block_end_string="}",
    variable_start_string="\\VAR{",
    variable_end_string="}",
    comment_start_string="\\#{",
    comment_end_string="}",
)


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters in text."""
    if not text:
        return ""
    special_chars = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for char, replacement in special_chars.items():
        text = text.replace(char, replacement)
    return text


def render_resume_to_latex(resume_data: dict) -> str:
    """Render a resume data dict to a LaTeX string using the Jinja2 template.

    Args:
        resume_data: The structured resume JSON from the LLM.

    Returns:
        A LaTeX document string.
    """
    try:
        template = jinja_env.get_template("resume.tex.j2")
        return template.render(resume=resume_data, escape=_escape_latex)
    except Exception as e:
        logger.error(f"Failed to render LaTeX template: {e}")
        # Fallback: return a minimal LaTeX document
        return _fallback_latex(resume_data)


def _fallback_latex(resume_data: dict) -> str:
    """Generate a minimal LaTeX resume when the template fails."""
    name = _escape_latex(resume_data.get("name", "Candidate"))
    summary = _escape_latex(resume_data.get("summary", ""))

    lines = [
        r"\documentclass[11pt,a4paper]{article}",
        r"\usepackage[margin=0.75in]{geometry}",
        r"\usepackage{enumitem}",
        r"\begin{document}",
        rf"\begin{{center}}\textbf{{\Large {name}}}\end{{center}}",
        r"\vspace{0.5em}",
    ]

    if summary:
        lines.append(rf"\noindent {summary}")
        lines.append(r"\vspace{1em}")

    # Experience
    experience = resume_data.get("experience", [])
    if experience:
        lines.append(r"\section*{Experience}")
        for exp in experience:
            title = _escape_latex(exp.get("title", ""))
            company = _escape_latex(exp.get("company", ""))
            date_range = _escape_latex(exp.get("date_range", ""))
            lines.append(rf"\textbf{{{title}}} -- {company} \hfill {date_range}")
            lines.append(r"\begin{itemize}[leftmargin=*,nosep]")
            for bullet in exp.get("bullets", []):
                lines.append(rf"  \item {_escape_latex(bullet)}")
            lines.append(r"\end{itemize}")
            lines.append(r"\vspace{0.5em}")

    # Projects
    projects = resume_data.get("projects", [])
    if projects:
        lines.append(r"\section*{Projects}")
        for proj in projects:
            title = _escape_latex(proj.get("title", ""))
            date_range = _escape_latex(proj.get("date_range", ""))
            tech = _escape_latex(proj.get("technologies", ""))
            lines.append(rf"\textbf{{{title}}} \hfill {date_range}")
            if tech:
                lines.append(rf"\\ \textit{{Technologies: {tech}}}")
            lines.append(r"\begin{itemize}[leftmargin=*,nosep]")
            for bullet in proj.get("bullets", []):
                lines.append(rf"  \item {_escape_latex(bullet)}")
            lines.append(r"\end{itemize}")
            lines.append(r"\vspace{0.5em}")

    # Skills
    skills = resume_data.get("skills", {})
    if skills:
        lines.append(r"\section*{Skills}")
        for category, skill_list in skills.items():
            if skill_list:
                cat_name = _escape_latex(category.replace("_", " ").title())
                skill_str = _escape_latex(", ".join(skill_list))
                lines.append(rf"\textbf{{{cat_name}:}} {skill_str} \\")

    lines.append(r"\end{document}")
    return "\n".join(lines)


def render_pdf(latex_content: str) -> str | None:
    """Compile LaTeX content to PDF using pdflatex.

    Args:
        latex_content: Full LaTeX document string.

    Returns:
        Absolute path to the generated PDF, or None if compilation fails.
    """
    # Check if pdflatex is available
    try:
        subprocess.run(["pdflatex", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.warning(
            "pdflatex not found. PDF generation disabled. "
            "Install texlive to enable PDF output."
        )
        return None

    pdf_id = str(uuid.uuid4())
    output_path = PDF_OUTPUT_DIR / f"{pdf_id}.pdf"

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        with open(tex_path, "w") as f:
            f.write(latex_content)

        try:
            # Run pdflatex twice for references
            for _ in range(2):
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            compiled_pdf = os.path.join(tmpdir, "resume.pdf")
            if os.path.exists(compiled_pdf):
                import shutil
                shutil.copy2(compiled_pdf, str(output_path))
                logger.info(f"Generated PDF: {output_path}")
                return str(output_path)
            else:
                logger.error(f"pdflatex did not produce a PDF. Stderr: {result.stderr[:500]}")
                return None
        except subprocess.TimeoutExpired:
            logger.error("pdflatex timed out")
            return None
        except Exception as e:
            logger.error(f"PDF compilation failed: {e}")
            return None
