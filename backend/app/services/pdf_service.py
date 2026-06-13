"""PDF rendering service – LaTeX/Jinja2 to PDF with dual-context escaping."""

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


# ---------------------------------------------------------------------------
# Dual-context LaTeX escaping
# ---------------------------------------------------------------------------

import re

# Structural fields (title, company, date_range) — escape everything including _
_LATEX_STRUCTURAL_CHARS = {
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}",
    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    "<": r"\textless{}", ">": r"\textgreater{}"
}

def escape_structural(text: str) -> str:
    """Escape special LaTeX characters in structural fields (titles, company names, dates).

    Escapes everything including underscores and braces — safe for fields that don't contain
    LaTeX formatting commands.
    """
    if not text:
        return ""
    # Escape backslash first to avoid double-escaping
    text = text.replace("\\", r"\textbackslash{}")
    for char, replacement in _LATEX_STRUCTURAL_CHARS.items():
        text = text.replace(char, replacement)
    return text


def escape_bullet(text: str) -> str:
    """Escape special LaTeX characters in bullet text.

    Preserves \\textbf{}, \\href{}, and other LaTeX commands that the LLM generates.
    Escapes & % $ # and unescaped underscores.
    """
    if not text:
        return ""
    # Escape basic special characters
    for char, replacement in [("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#")]:
        text = text.replace(char, replacement)
    
    # Escape underscores that aren't already escaped
    text = re.sub(r'(?<!\\)_', r'\_', text)
    return text


# Backward compatibility alias
_escape_latex = escape_structural


def render_resume_to_latex(resume_data: dict, profile=None) -> str:
    """Render a resume data dict to a LaTeX string using the Jinja2 template.

    Args:
        resume_data: The structured resume JSON from the generation pipeline.
        profile: UserProfile ORM object for header info.

    Returns:
        A LaTeX document string.
    """
    try:
        template = jinja_env.get_template("resume.tex.j2")
        profile_dict = {}
        if profile:
            profile_dict = {
                "name": profile.name or "",
                "email": profile.email or "",
                "phone": profile.phone or "",
                "github": profile.github or "",
                "linkedin": profile.linkedin or "",
                "location": profile.location or "",
                "portfolio": getattr(profile, "portfolio", "") or "",
                "college": profile.college or "",
                "college_years": f"{getattr(profile, 'college_start_year', '') or ''} \u2013 {profile.graduation_year or ''}".strip(" \u2013"),
                "degree": profile.degree or "",
                "coursework": profile.coursework or "",
            }
        return template.render(
            resume=resume_data,
            profile=profile_dict,
            esc=escape_structural,
            esc_bullet=escape_bullet,
            escape=escape_structural,  # backward compat
        )
    except Exception as e:
        logger.error(f"Failed to render LaTeX template: {e}")
        # Fallback: return a minimal LaTeX document
        return _fallback_latex(resume_data)


def _fallback_latex(resume_data: dict) -> str:
    """Generate a minimal LaTeX resume when the template fails."""
    name = escape_structural(resume_data.get("name", "Candidate"))
    summary = escape_structural(resume_data.get("summary", ""))

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
            title = escape_structural(exp.get("title", ""))
            company = escape_structural(exp.get("company", ""))
            date_range = escape_structural(exp.get("date_range", ""))
            lines.append(rf"\textbf{{{title}}} -- {company} \hfill {date_range}")
            lines.append(r"\begin{itemize}[leftmargin=*,nosep]")
            for bullet in exp.get("bullets", []):
                lines.append(rf"  \item {escape_bullet(bullet)}")
            lines.append(r"\end{itemize}")
            lines.append(r"\vspace{0.5em}")

    # Projects
    projects = resume_data.get("projects", [])
    if projects:
        lines.append(r"\section*{Projects}")
        for proj in projects:
            title = escape_structural(proj.get("title", ""))
            date_range = escape_structural(proj.get("date_range", ""))
            tech = escape_structural(proj.get("technologies", ""))
            lines.append(rf"\textbf{{{title}}} \hfill {date_range}")
            if tech:
                lines.append(rf"\\ \textit{{Technologies: {tech}}}")
            lines.append(r"\begin{itemize}[leftmargin=*,nosep]")
            for bullet in proj.get("bullets", []):
                lines.append(rf"  \item {escape_bullet(bullet)}")
            lines.append(r"\end{itemize}")
            lines.append(r"\vspace{0.5em}")

    # Skills
    skills = resume_data.get("skills", {})
    if skills:
        lines.append(r"\section*{Skills}")
        for category, skill_list in skills.items():
            if skill_list:
                cat_name = escape_structural(category.replace("_", " ").title())
                skill_str = escape_structural(", ".join(skill_list))
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
            latex_errors = []
            for _ in range(2):
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                # Capture LaTeX errors
                if result.returncode != 0:
                    for line in result.stdout.split("\n"):
                        if line.startswith("! ") or "LaTeX Error" in line:
                            latex_errors.append(line.strip())

            if latex_errors:
                logger.warning(f"LaTeX warnings/errors: {'; '.join(latex_errors[:5])}")

            compiled_pdf = os.path.join(tmpdir, "resume.pdf")
            if os.path.exists(compiled_pdf):
                import shutil
                shutil.copy2(compiled_pdf, str(output_path))
                logger.info(f"Generated PDF: {output_path}")
                return str(output_path)
            else:
                logger.error(f"pdflatex did not produce a PDF. Errors: {'; '.join(latex_errors[:3])}")
                return None
        except subprocess.TimeoutExpired:
            logger.error("pdflatex timed out")
            return None
        except Exception as e:
            logger.error(f"PDF compilation failed: {e}")
            return None

def get_pdf_page_count(pdf_path: str) -> int:
    """Get the number of pages in a compiled PDF using pdfinfo."""
    if not pdf_path or not os.path.exists(pdf_path):
        return 0
    try:
        result = subprocess.run(
            ["pdfinfo", pdf_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        for line in result.stdout.split("\n"):
            if line.startswith("Pages:"):
                return int(line.split(":")[1].strip())
    except Exception as e:
        logger.warning(f"Could not determine PDF page count: {e}")
    return 1
