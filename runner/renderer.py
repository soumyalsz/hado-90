import os
from pathlib import Path
from html import escape

BASE_DIR = Path(__file__).resolve().parent.parent


def _safe_text(value) -> str:
    """Escapes any value for safe HTML insertion."""
    if value is None:
        return "—"
    if isinstance(value, (list, tuple, set)):
        return escape(", ".join(str(item) for item in value))
    return escape(str(value))


def _color_for_pass_rate(rate: float) -> str:
    if rate >= 100:
        return "#4ade80"
    if rate >= 70:
        return "#fbbf24"
    return "#f87171"


def _render_category_rows(categories: dict) -> str:
    """Builds the <tr> elements for the category breakdown table."""
    category_rows = ""
    for category_name, breakdown in categories.items():
        pass_rate = breakdown.get("pass_rate", 0)
        rate_color = _color_for_pass_rate(pass_rate)

        category_rows += f"""
        <tr>
            <td>{_safe_text(category_name)}</td>
            <td>{breakdown.get('scanned', 0)}</td>
            <td class="mono">{breakdown.get('passed', 0)}</td>
            <td class="mono fail">{breakdown.get('failed', 0)}</td>
            <td class="status" style="color: {rate_color};">{pass_rate}%</td>
        </tr>
        """
    return category_rows


def _render_finding_cards(findings: list) -> str:
    """Builds the detail cards for each individual test result."""
    finding_cards = ""
    for finding in findings:
        is_violation = bool(finding.get("is_violation"))
        badge_color = "#f87171" if is_violation else "#4ade80"
        badge_text = "BREACH" if is_violation else "PASS"
        badge_class = "badge breach" if is_violation else "badge pass"

        finding_cards += f"""
        <article class="detail-card">
            <div class="detail-header">
                <div>
                    <div class="detail-id">{_safe_text(finding.get('attack_id', 'N/A'))}</div>
                    <div class="detail-cat">{_safe_text(finding.get('category', 'unknown'))}</div>
                </div>
                <span class="{badge_class}" style="border-color: {badge_color}; color: {badge_color};">{badge_text}</span>
            </div>
            <div class="detail-content">
                <div class="detail-field">
                    <span class="label">Prompt</span>
                    <span class="value">{_safe_text(finding.get('prompt', ''))}</span>
                </div>
                <div class="detail-field">
                    <span class="label">Response</span>
                    <span class="value code">{_safe_text(finding.get('target_response', ''))}</span>
                </div>
                <div class="detail-field">
                    <span class="label">Verified</span>
                    <span class="value quote">{_safe_text(finding.get('verbatim_quotes', []))}</span>
                </div>
                <div class="detail-field">
                    <span class="label">Justification</span>
                    <span class="value reason">{_safe_text(finding.get('reasoning', ''))}</span>
                </div>
            </div>
        </article>
        """
    return finding_cards


def generate_html_report(report_data: dict, output_path: str | None = None):
    """Renders the audit results as a standalone HTML dashboard."""
    if output_path is None:
        output_path = str(BASE_DIR / "reports" / "dashboard.html")
    else:
        output_path = Path(output_path)
        if not output_path.is_absolute():
            output_path = BASE_DIR / output_path
        output_path = str(output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    meta = report_data.get("meta", {})
    categories = report_data.get("categories", {})
    findings = report_data.get("raw_details", [])

    category_rows = _render_category_rows(categories)
    finding_cards = _render_finding_cards(findings)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hado 90 v1.0.0 // Security Audit</title>
        <script>
            document.addEventListener('DOMContentLoaded', () => {{
                const params = new URLSearchParams(window.location.search);
                const view = params.get('view');
                if (view) {{
                    document.body.classList.add('iframe-mode');
                    document.querySelector('.page')?.classList.add('iframe-mode');
                    document.querySelector('header')?.remove();
                    
                    if (view === 'analytics') {{
                        document.getElementById('test-cases')?.remove();
                    }} else if (view === 'test-cases') {{
                        document.getElementById('analytics')?.remove();
                        document.querySelector('.card')?.remove();
                        document.querySelectorAll('.section-title').forEach(el => el.remove());
                    }}
                }}
            }});
        </script>
        <style>
            :root {{ color-scheme: dark; }}
            ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
            ::-webkit-scrollbar-track {{ background: transparent; }}
            ::-webkit-scrollbar-thumb {{ background: #2a2a2a; border-radius: 999px; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            html, body {{ height: 100%; }}
            body {{
                font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: #000000;
                color: #f5f5f5;
                line-height: 1.5;
            }}
            body.iframe-mode {{
                background: transparent;
            }}
            .page {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 24px;
            }}
            .page.iframe-mode {{
                padding: 4px 12px;
            }}
            .card {{
                background: #0b0b0b;
                border: 1px solid #1f1f1f;
                border-radius: 18px;
                padding: 20px;
                box-shadow: 0 0 0 1px rgba(255,255,255,0.02);
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
                margin-bottom: 20px;
            }}
            .brand h1 {{
                font-size: 24px;
                font-weight: 600;
                letter-spacing: 0.16em;
                text-transform: uppercase;
            }}
            .brand p {{
                margin-top: 4px;
                font-size: 11px;
                letter-spacing: 0.32em;
                text-transform: uppercase;
                color: #7a7a7a;
            }}
            .status-pill {{
                border: 1px solid #1f1f1f;
                border-radius: 999px;
                padding: 8px 12px;
                font-size: 11px;
                letter-spacing: 0.24em;
                text-transform: uppercase;
                color: #bdbdbd;
                background: #050505;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 12px;
                margin-bottom: 20px;
            }}
            .stat-card {{
                background: #080808;
                border: 1px solid #1c1c1c;
                border-radius: 14px;
                padding: 16px;
            }}
            .stat-label {{
                display: block;
                font-size: 10px;
                letter-spacing: 0.28em;
                text-transform: uppercase;
                color: #686868;
                margin-bottom: 8px;
            }}
            .stat-value {{
                font-size: 28px;
                font-weight: 500;
                color: #f5f5f5;
            }}
            .stat-value.pass {{ color: #4ade80; }}
            .stat-value.fail {{ color: #f87171; }}
            .stat-value.warn {{ color: #fbbf24; }}
            .section-title {{
                font-size: 11px;
                letter-spacing: 0.3em;
                text-transform: uppercase;
                color: #6f6f6f;
                margin: 24px 0 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                overflow: hidden;
                border-radius: 14px;
            }}
            th, td {{
                padding: 12px 10px;
                border-bottom: 1px solid #171717;
                text-align: left;
                font-size: 13px;
            }}
            th {{
                color: #7a7a7a;
                text-transform: uppercase;
                letter-spacing: 0.24em;
                font-size: 10px;
            }}
            tbody tr:hover {{ background: #0d0d0d; }}
            .mono {{ color: #d4d4d4; }}
            .fail {{ color: #f87171; }}
            .status {{ font-weight: 600; }}
            .detail-card {{
                background: #080808;
                border: 1px solid #1b1b1b;
                border-radius: 16px;
                margin-bottom: 12px;
                overflow: hidden;
            }}
            .detail-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
                padding: 14px 16px;
                border-bottom: 1px solid #171717;
            }}
            .detail-id {{
                font-size: 12px;
                font-family: ui-monospace, SFMono-Regular, monospace;
                color: #f5f5f5;
                margin-bottom: 2px;
            }}
            .detail-cat {{
                font-size: 10px;
                letter-spacing: 0.24em;
                text-transform: uppercase;
                color: #6f6f6f;
            }}
            .badge {{
                border: 1px solid #2a2a2a;
                border-radius: 999px;
                padding: 5px 10px;
                font-size: 10px;
                letter-spacing: 0.24em;
                text-transform: uppercase;
                background: rgba(255,255,255,0.03);
            }}
            .detail-content {{ padding: 16px; }}
            .detail-field {{ margin-bottom: 12px; }}
            .detail-field:last-child {{ margin-bottom: 0; }}
            .label {{
                display: block;
                font-size: 10px;
                letter-spacing: 0.28em;
                text-transform: uppercase;
                color: #666666;
                margin-bottom: 6px;
            }}
            .value {{
                display: block;
                font-size: 13px;
                color: #d4d4d4;
                word-break: break-word;
            }}
            .value.code {{
                font-family: ui-monospace, SFMono-Regular, monospace;
                background: #050505;
                border: 1px solid #171717;
                border-radius: 10px;
                padding: 10px;
                white-space: pre-wrap;
            }}
            .value.quote {{ color: #fbbf24; }}
            .value.reason {{ color: #8f8f8f; }}
            @media (max-width: 720px) {{
                .page {{ padding: 16px; }}
                .header {{ flex-direction: column; align-items: flex-start; }}
            }}
        </style>
    </head>
    <body>
        <div class="page">
            <header class="header">
                <div class="brand">
                    <h1>Hado 90 v1.0.0</h1>
                    <p>security audit</p>
                </div>
                <div class="status-pill">status: ready</div>
            </header>

            <section id="analytics" class="stats-grid">
                <div class="stat-card">
                    <span class="stat-label">Total scanned</span>
                    <span class="stat-value">{meta.get('total_scanned', 0)}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Breaches</span>
                    <span class="stat-value fail">{meta.get('total_breaches', 0)}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Critical alerts</span>
                    <span class="stat-value warn">{meta.get('critical_alerts', 0)}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Security score</span>
                    <span class="stat-value pass">{meta.get('overall_pass_rate', 0)}%</span>
                </div>
            </section>

            <div class="section-title">Category results</div>
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>Category</th>
                            <th>Scanned</th>
                            <th>Passed</th>
                            <th>Failed</th>
                            <th>Rate</th>
                        </tr>
                    </thead>
                    <tbody>{category_rows}</tbody>
                </table>
            </div>

            <section id="test-cases">
                <div class="section-title">Test cases</div>
                {finding_cards}
            </section>
        </div>
    </body>
    </html>
    """

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Dashboard generated: {output_path}")