"""Cria o relatório DOCX de validação do Sergipe Traffic AI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Relatorio_validacao_Sergipe_Traffic_AI.docx"
SUMMARY_PATH = (
    ROOT
    / "experiments"
    / "output"
    / "comparison"
    / "controller_comparison_summary.json"
)
REPORT_FIGURES = ROOT / "experiments" / "output" / "report"
CHECKIN_REPORT = (
    ROOT / "experiments" / "output" / "checkin2" / "checkin2_report.json"
)

BLACK = "000000"
NAVY = "1F4E79"
TEAL = "2A9D8F"
LIGHT_BLUE = "EAF2F8"
LIGHT_GRAY = "F2F4F5"
BORDER = "D9D9D9"
GRAY = "5B6573"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_borders(cell, color: str = BORDER, size: str = "6") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def mark_header_row(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_repeat_table_header(row) -> None:
    mark_header_row(row)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    tr_pr.append(cant_split)


def set_run_font(run, name="Arial", size=None, bold=None, color=BLACK, italic=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def add_hyperlink(paragraph, text: str, url: str, color=NAVY, underline=True):
    part = paragraph.part
    relationship_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    new_run = OxmlElement("w:r")
    run_properties = OxmlElement("w:rPr")
    color_node = OxmlElement("w:color")
    color_node.set(qn("w:val"), color)
    run_properties.append(color_node)
    if underline:
        underline_node = OxmlElement("w:u")
        underline_node.set(qn("w:val"), "single")
        run_properties.append(underline_node)
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), "Arial")
    fonts.set(qn("w:hAnsi"), "Arial")
    run_properties.append(fonts)
    new_run.append(run_properties)
    text_node = OxmlElement("w:t")
    text_node.text = text
    new_run.append(text_node)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)


def add_body(doc: Document, text: str, bold_lead: str | None = None):
    paragraph = doc.add_paragraph(style="Normal")
    if bold_lead and text.startswith(bold_lead):
        lead = paragraph.add_run(bold_lead)
        set_run_font(lead, bold=True)
        rest = paragraph.add_run(text[len(bold_lead) :])
        set_run_font(rest)
    else:
        run = paragraph.add_run(text)
        set_run_font(run)
    return paragraph


def add_bullet(doc: Document, text: str):
    paragraph = doc.add_paragraph(style="List Bullet")
    run = paragraph.add_run(text)
    set_run_font(run)
    return paragraph


def add_table(doc: Document, headers: list[str], rows: Iterable[Iterable[str]], widths: list[float]):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    header = table.rows[0]
    set_repeat_table_header(header)
    prevent_row_split(header)
    for index, (cell, header_text) in enumerate(zip(header.cells, headers)):
        cell.width = Inches(widths[index])
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(cell, NAVY)
        set_cell_borders(cell)
        set_cell_margins(cell)
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(header_text)
        set_run_font(run, size=9, bold=True, color="FFFFFF")

    for row_index, values in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        for index, (cell, value) in enumerate(zip(row.cells, values)):
            cell.width = Inches(widths[index])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_borders(cell)
            set_cell_margins(cell)
            if row_index % 2 == 1:
                set_cell_shading(cell, LIGHT_GRAY)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(str(value))
            set_run_font(run, size=8.7)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_caption(doc: Document, text: str):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(9)
    run = paragraph.add_run(text)
    set_run_font(run, size=8.5, color=GRAY, italic=True)
    return paragraph


def add_figure(doc: Document, path: Path, width: float, caption: str):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    run.add_picture(str(path), width=Inches(width))
    drawing = run._element.xpath(".//wp:docPr")
    if drawing:
        drawing[0].set("descr", caption)
        drawing[0].set("title", caption)
    add_caption(doc, caption)


def add_source_link(doc: Document, label: str, url: str):
    paragraph = doc.add_paragraph(style="Normal")
    run = paragraph.add_run(label + ": ")
    set_run_font(run, size=9)
    add_hyperlink(paragraph, url, url)
    return paragraph


def configure_styles(doc: Document):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string(BLACK)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.12

    for style_name, size, before, after in (
        ("Title", 24, 0, 8),
        ("Heading 1", 16, 16, 6),
        ("Heading 2", 12, 10, 4),
    ):
        style = styles[style_name]
        style.font.name = "Arial"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(BLACK)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    subtitle = styles["Subtitle"]
    subtitle.font.name = "Arial"
    subtitle._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    subtitle._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    subtitle.font.size = Pt(12)
    subtitle.font.color.rgb = RGBColor.from_string(BLACK)

    for style_name in ("List Bullet",):
        style = styles[style_name]
        style.font.name = "Arial"
        style.font.size = Pt(10.5)
        style.font.color.rgb = RGBColor.from_string(BLACK)


def remove_paragraph_borders(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    borders = p_pr.find(qn("w:pBdr"))
    if borders is not None:
        p_pr.remove(borders)


def build_report() -> Path:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    json.loads(CHECKIN_REPORT.read_text(encoding="utf-8"))
    controllers = summary["controllers"]
    fixed = controllers["FixedTrafficController"]["metrics"]
    adaptive = controllers["AdaptiveTrafficController"]["metrics"]
    qlearning = controllers["QLearningAgent"]["metrics"]

    wait_fixed = fixed["average_completed_wait_s"]["mean"]
    wait_adaptive = adaptive["average_completed_wait_s"]["mean"]
    wait_q = qlearning["average_completed_wait_s"]["mean"]
    queue_fixed = fixed["mean_queue"]["mean"]
    queue_adaptive = adaptive["mean_queue"]["mean"]
    queue_q = qlearning["mean_queue"]["mean"]
    throughput_fixed = fixed["throughput_per_min"]["mean"]
    throughput_adaptive = adaptive["throughput_per_min"]["mean"]
    throughput_q = qlearning["throughput_per_min"]["mean"]

    wait_adaptive_pct = 100 * (wait_fixed - wait_adaptive) / wait_fixed
    wait_q_pct = 100 * (wait_fixed - wait_q) / wait_fixed
    queue_adaptive_pct = 100 * (queue_fixed - queue_adaptive) / queue_fixed
    queue_q_pct = 100 * (queue_fixed - queue_q) / queue_fixed
    throughput_adaptive_pct = 100 * (throughput_adaptive - throughput_fixed) / throughput_fixed
    throughput_q_pct = 100 * (throughput_q - throughput_fixed) / throughput_fixed
    wait_q_vs_adaptive_pct = 100 * (wait_adaptive - wait_q) / wait_adaptive
    queue_q_vs_adaptive_pct = 100 * (queue_adaptive - queue_q) / queue_adaptive
    throughput_q_vs_adaptive_pct = 100 * (throughput_q - throughput_adaptive) / throughput_adaptive

    doc = Document()
    configure_styles(doc)
    section = doc.sections[0]
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)

    footer = section.footer
    footer_paragraph = footer.paragraphs[0]
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer_paragraph.add_run("Sergipe Traffic AI  |  Relatório de validação  |  ")
    set_run_font(footer_run, size=8, color=GRAY)
    add_page_number(footer_paragraph)

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    remove_paragraph_borders(title)
    title_style_borders = doc.styles["Title"]._element.pPr.find(qn("w:pBdr"))
    if title_style_borders is not None:
        doc.styles["Title"]._element.pPr.remove(title_style_borders)
    title_run = title.add_run("Relatório de validação do Sergipe Traffic AI")
    set_run_font(title_run, size=24, bold=True, color=BLACK)
    subtitle = doc.add_paragraph(style="Subtitle")
    subtitle_run = subtitle.add_run(
        "Integração territorial, mapa OpenStreetMap e comparação entre controle fixo, adaptativo e Q-learning"
    )
    set_run_font(subtitle_run, size=12, color=BLACK)
    date_paragraph = doc.add_paragraph()
    date_run = date_paragraph.add_run("Aracaju, Sergipe  |  14 de novembro de 2026")
    set_run_font(date_run, size=9.5, color=GRAY)

    doc.add_paragraph()
    doc.add_heading("Sumário executivo", level=1)
    add_body(
        doc,
        "Este relatório consolida a etapa de validação do Sergipe Traffic AI. O cenário piloto é inspirado no cruzamento entre a Avenida Augusto Franco e a Avenida Desembargador Maynard / Barão de Maruim, em Aracaju. A rede viária real foi obtida do OpenStreetMap por meio da Overpass API; o IBGE fornece os limites oficiais e os indicadores demográficos usados para estimar a demanda relativa e simular horários de pico. As taxas-base continuam sendo uma hipótese de prototipagem, portanto os resultados medem eficiência dentro do simulador e não representam uma medição de campo.",
    )
    add_body(
        doc,
        f"A conclusão principal é que o Q-learning foi o melhor nas métricas de espera e fila no experimento controlado: apresentou espera média de {wait_q:.2f} s e fila média de {queue_q:.2f} veículos. O controlador adaptativo ficou muito próximo ({wait_adaptive:.2f} s e {queue_adaptive:.2f} veículos) e teve o maior throughput ({throughput_adaptive:.2f} contra {throughput_q:.2f} veículos/min). O controlador fixo foi o pior baseline ({wait_fixed:.2f} s, {queue_fixed:.2f} veículos e {throughput_fixed:.2f} veículos/min). A diferença entre Q-learning e adaptativo é pequena, portanto a escolha depende da prioridade entre fluidez e redução de espera.",
        bold_lead="A conclusão principal é que o Q-learning foi o melhor nas métricas de espera e fila no experimento controlado: ",
    )
    add_bullet(doc, f"Q-learning versus fixo: {wait_q_pct:.1f}% menos espera, {queue_q_pct:.1f}% menos fila e {throughput_q_pct:.1f}% mais throughput.")
    add_bullet(doc, f"Adaptativo versus fixo: {wait_adaptive_pct:.1f}% menos espera, {queue_adaptive_pct:.1f}% menos fila e {throughput_adaptive_pct:.1f}% mais throughput.")
    add_bullet(doc, "Decisão recomendada: usar Q-learning quando a prioridade for reduzir espera e fila; manter o adaptativo como alternativa operacional simples, explicável e com maior throughput médio neste recorte.")

    doc.add_heading("1 Escopo e pergunta de análise", level=1)
    add_body(doc, "A pergunta de pesquisa é: um controlador semafórico baseado em observação do trânsito consegue melhorar as métricas de mobilidade em relação a um controlador de tempo fixo em cenários simulados inspirados em Sergipe? Para responder, foram executados episódios pareados com a mesma configuração de demanda, a mesma duração e as mesmas seeds para os três métodos.")
    add_body(doc, "Neste documento, os termos são usados assim: controle estático ou fixo é o ciclo de tempos predeterminados; controle dinâmico ou adaptativo é a heurística que observa filas e espera e troca de fase por regras; Q-learning é a política de aprendizado por reforço que solicita trocas a partir de estados discretizados. A máquina de segurança mantém amarelo, todos-vermelhos, tempo mínimo e tempo máximo de verde em todos os casos.")

    doc.add_heading("2 Dados e contexto territorial", level=1)
    add_body(doc, "A integração de dados é híbrida. O IBGE fornece a referência territorial oficial, população e densidade do Censo 2022; o OpenStreetMap fornece a geometria e os atributos da rede viária; a demanda é estimada a partir de taxas-base, um fator demográfico relativo e um perfil de horários de pico. Ainda não há contagens observadas do cruzamento no projeto.")
    add_table(
        doc,
        ["Fonte", "Dado incorporado", "Uso no projeto"],
        [
            ["IBGE", "Malhas de Sergipe e Aracaju; população 2022 de 602.757 habitantes e densidade de 3.308,89 hab/km².", "Limites oficiais, contexto demográfico, estimativa relativa da demanda e períodos de pico."],
            ["OpenStreetMap / Overpass", "355 vias no raio de 800 m; 274 nomeadas; 129 com atributo one-way; avenidas do cenário encontradas.", "Mapa contextual e atributos da rede viária real."],
            ["Cenário sintético", "Taxas de chegada, composição da frota, divisão por sentido e seeds reproduzíveis.", "Geração controlada de demanda para comparar controladores."],
        ],
        [1.35, 2.75, 2.6],
    )

    doc.add_heading("2.1 Indicadores do IBGE", level=2)
    add_body(doc, "Os indicadores abaixo contextualizam a escala urbana do estudo e entram no simulador como fator relativo sobre as taxas-base. Para Aracaju, a referência demográfica é 1,00 porque o cenário foi calibrado em relação ao próprio município. População e densidade não substituem contagens horárias, matriz origem-destino ou dados de sensores.")
    add_table(
        doc,
        ["Recorte", "Código", "População 2022", "Área territorial", "Densidade 2022"],
        [
            ["Sergipe", "28", "2.210.004", "21.938,188 km²", "100,74 hab/km²"],
            ["Aracaju", "2800308", "602.757", "182,163 km²", "3.308,89 hab/km²"],
        ],
        [1.2, 1.0, 1.35, 1.55, 1.6],
    )
    add_caption(doc, "Tabela 2. Indicadores territoriais oficiais usados como contexto. População e densidade: Censo 2022; área: referência territorial do IBGE.")

    doc.add_heading("2.2 Estimativa de demanda e horários de pico", level=2)
    add_body(doc, "A demanda do cenário combina três componentes: taxa-base por eixo, fator demográfico relativo e multiplicador de faixa horária. A taxa-base permanece explícita no arquivo do cenário; o fator demográfico é calculado a partir da razão entre população/densidade do município e a referência de Aracaju; o multiplicador representa a variação esperada ao longo do dia. Como Aracaju é a referência atual, o fator demográfico é 1,00 e os horários modificam a demanda em relação à taxa-base.")
    add_table(
        doc,
        ["Período", "Horário", "Multiplicador", "Aplicação"],
        [
            ["Madrugada", "00:00–06:00", "0,60×", "Reduz a chegada relativa"],
            ["Pico da manhã", "06:00–10:00", "1,30×", "Aumenta a chegada relativa"],
            ["Entre picos", "10:00–16:00", "0,90×", "Mantém fluxo intermediário"],
            ["Pico da tarde", "16:00–20:00", "1,35×", "Aumenta a chegada relativa"],
            ["Noite", "20:00–24:00", "0,70×", "Reduz a chegada relativa"],
        ],
        [1.5, 1.25, 1.2, 3.05],
    )
    add_caption(doc, "Tabela 3. Perfil horário aplicado pelo simulador. O episódio visual inicia às 07:00 e, portanto, começa no pico da manhã.")

    add_figure(
        doc,
        REPORT_FIGURES / "osm_context_map.png",
        4.7,
        "Figura 1. Mapa de contexto do entorno real do cenário piloto. As linhas vermelhas destacam as vias associadas ao cenário; o ponto preto é a referência aproximada usada na consulta.",
    )
    add_body(doc, "A consulta OSM foi feita em torno de -10.9187, -37.06943, com raio de 800 m. O mapa mostra a rede real do entorno e serve para contextualizar o protótipo. A simulação ainda utiliza um cruzamento esquemático ampliado: os veículos não percorrem automaticamente a geometria OSM. Essa separação é importante para não apresentar o resultado como uma reprodução topográfica ou uma calibração de campo.")

    doc.add_heading("3 Metodologia experimental", level=1)
    add_table(
        doc,
        ["Elemento", "Configuração utilizada"],
        [
            ["Cenário", "Avenida Barão de Maruim / Desembargador Maynard × Avenida Augusto Franco; referência geográfica aproximada em Aracaju/SE."],
            ["Demanda", "Taxas-base de 0,85 e 0,75 veículos/s; fator demográfico IBGE de 1,00 para Aracaju; início às 07:00 com multiplicador 1,30× no pico da manhã."],
            ["Frota", "72% carros, 18% motocicletas e 10% ônibus; composição sintética."],
            ["Simulação", "600 s por episódio, passo de 0,2 s, seeds 1000 a 1019; 20 episódios por controlador."],
            ["Treinamento", "Q-learning tabular treinado por 200 episódios de 600 s; avaliação sem exploração, epsilon = 0."],
            ["Segurança", "Verde → amarelo → todos-vermelhos → verde oposto; mínimo 15 s, máximo 60 s de verde; amarelo 4 s e todos-vermelhos 2 s."],
        ],
        [1.55, 5.15],
    )

    doc.add_heading("3.1 Indicadores de eficiência", level=2)
    add_body(doc, "A espera média considera os veículos concluídos; a fila média é a média temporal do total de veículos em estado de fila; o throughput é o número de veículos concluídos por minuto simulado. A leitura conjunta evita escolher um método que reduza uma métrica sacrificando as demais.")
    add_table(
        doc,
        ["Indicador", "Interpretação", "Preferência"],
        [
            ["Espera média dos concluídos", "Tempo acumulado parado antes de concluir a travessia.", "Menor"],
            ["Fila média", "Pressão média sobre as aproximações do cruzamento.", "Menor"],
            ["Throughput", "Veículos concluídos por minuto de simulação.", "Maior"],
            ["Máximo de fila", "Pico de congestionamento observado no episódio.", "Menor"],
        ],
        [2.0, 3.6, 1.1],
    )

    doc.add_heading("3.2 Cenários de sensibilidade", level=2)
    add_body(
        doc,
        "A tabela resume variações de pesos que podem ser usadas para demonstrar como o controlador reage a diferentes condições. São cenários propostos para a próxima rodada de experimentos; eles não foram misturados ao ranking apresentado na seção 4. Em cada linha, B/A representa a taxa de chegada nos eixos Barão/Maynard e Augusto Franco; C/M/O representa carro, motocicleta e ônibus; F/E/T representa os pesos de fila, espera e throughput na recompensa do Q-learning.",
    )
    add_table(
        doc,
        ["Cenário", "Demanda B/A (veh/s)", "Frota C/M/O (%)", "Recompensa F/E/T", "Objetivo"],
        [
            ["Base", "0,85 / 0,75", "72 / 18 / 10", "1,00 / 0,05 / 0,50", "Referência atual"],
            ["Pico Barão", "1,10 / 0,60", "72 / 18 / 10", "1,00 / 0,05 / 0,50", "Testar desequilíbrio para Barão"],
            ["Pico Augusto", "0,60 / 1,00", "72 / 18 / 10", "1,00 / 0,05 / 0,50", "Testar desequilíbrio para Augusto"],
            ["Frota pesada", "0,85 / 0,75", "55 / 15 / 30", "1,00 / 0,05 / 0,50", "Avaliar efeito de ônibus"],
            ["Prioridade fluidez", "0,85 / 0,75", "72 / 18 / 10", "0,70 / 0,03 / 1,00", "Valorizar veículos concluídos"],
        ],
        [1.05, 1.35, 1.35, 1.55, 1.4],
    )
    add_caption(doc, "Tabela 4. Resumo de pesos para análise de sensibilidade. Os cenários são propostas de teste, não resultados já executados.")

    doc.add_heading("4 Resultados da comparação", level=1)
    add_figure(
        doc,
        REPORT_FIGURES / "controller_comparison.png",
        6.55,
        "Figura 2. Médias e desvios-padrão da comparação pareada em 20 episódios de 600 s.",
    )
    add_table(
        doc,
        ["Controlador", "Espera média (s)", "Fila média", "Throughput (veh/min)", "Posição"],
        [
            ["Q-learning", f"{wait_q:.2f} ± {qlearning['average_completed_wait_s']['std']:.2f}", f"{queue_q:.2f} ± {qlearning['mean_queue']['std']:.2f}", f"{throughput_q:.2f} ± {qlearning['throughput_per_min']['std']:.2f}", "1º"],
            ["Adaptativo", f"{wait_adaptive:.2f} ± {adaptive['average_completed_wait_s']['std']:.2f}", f"{queue_adaptive:.2f} ± {adaptive['mean_queue']['std']:.2f}", f"{throughput_adaptive:.2f} ± {adaptive['throughput_per_min']['std']:.2f}", "2º"],
            ["Fixo", f"{wait_fixed:.2f} ± {fixed['average_completed_wait_s']['std']:.2f}", f"{queue_fixed:.2f} ± {fixed['mean_queue']['std']:.2f}", f"{throughput_fixed:.2f} ± {fixed['throughput_per_min']['std']:.2f}", "3º"],
        ],
        [1.25, 1.55, 1.25, 1.65, 0.7],
    )
    add_caption(doc, "Tabela 5. Resultado médio ± desvio-padrão. A posição considera espera, fila e throughput em conjunto.")

    doc.add_heading("4.1 Ganho relativo ao baseline", level=2)
    add_body(doc, f"O Q-learning reduziu a espera média em {wait_q_pct:.1f}% em relação ao fixo, reduziu a fila média em {queue_q_pct:.1f}% e aumentou o throughput em {throughput_q_pct:.1f}%. O adaptativo também superou o fixo, com ganhos de {wait_adaptive_pct:.1f}%, {queue_adaptive_pct:.1f}% e {throughput_adaptive_pct:.1f}%, respectivamente.")
    add_body(doc, f"A diferença entre Q-learning e adaptativo é pequena na média: o Q-learning teve {wait_q_vs_adaptive_pct:.2f}% menos espera e {queue_q_vs_adaptive_pct:.2f}% menos fila, mas {abs(throughput_q_vs_adaptive_pct):.2f}% menos throughput. Isso indica que, neste cenário e sob esta demanda, ambos se beneficiam de reagir às filas; o Q-learning favorece a redução da espera, enquanto a heurística adaptativa conclui ligeiramente mais veículos.")
    add_body(doc, "A leitura pareada deve ser interpretada como evidência de proximidade entre os dois métodos, não como uma superioridade absoluta. A conclusão depende do peso atribuído a espera, fila e throughput e deve ser reavaliada com mais seeds, horários e calibração observada.")

    doc.add_heading("5 Discussão e decisão", level=1)
    add_body(doc, "Decisão recomendada: classificar o Q-learning como o controlador preferível quando a prioridade do cenário for reduzir espera e fila. O adaptativo deve permanecer como alternativa operacional explicável, pois alcançou o maior throughput médio neste recorte. Ambos mantêm a mesma camada de segurança que impede saltos diretos entre verdes conflitantes.", bold_lead="Decisão recomendada: ")
    add_body(doc, "A decisão deve ser apresentada com uma ressalva: o ganho adicional do Q-learning sobre o adaptativo é modesto. O adaptativo é mais simples de explicar, não depende de treinamento e é uma boa alternativa de fallback. Em uma implantação real, seria razoável operar com o adaptativo como baseline operacional e habilitar o Q-learning somente depois de calibração com dados observados, testes de segurança e monitoramento de desempenho.")
    add_body(doc, "O controlador fixo permanece importante como baseline científico. Ele fornece uma referência sem aprendizado e evidencia que, para a demanda desigual e variável do cenário, um ciclo rígido perde desempenho frente a políticas que observam o estado das filas.")

    doc.add_heading("6 Limitações e validade dos resultados", level=1)
    add_bullet(doc, "A demanda é uma estimativa relativa: as taxas-base, a composição da frota e a divisão por sentido foram definidas para prototipagem; população e densidade do IBGE apenas modulam o cenário e não são contagens de tráfego.")
    add_bullet(doc, "O OSM fornece rede viária, nomes e atributos geométricos; não fornece, por si só, volume de tráfego, tempo de espera ou distribuição observada de veículos.")
    add_bullet(doc, "A interseção simulada é esquemática e ampliada. A geometria OSM é contextual e ainda não é percorrida pelos veículos do motor de simulação.")
    add_bullet(doc, "A comparação usa 20 seeds e um único regime de demanda de 600 s. A conclusão é válida para este experimento; não deve ser extrapolada diretamente para a operação real de Aracaju.")
    add_bullet(doc, "O documento apresenta médias e desvios-padrão; ainda é recomendável acrescentar intervalos de confiança, testes pareados e análise de sensibilidade dos hiperparâmetros.")
    add_bullet(doc, "Pedestres, ciclistas, ciclovias e veículos de emergência ainda não estão implementados no ambiente avaliado.")

    doc.add_heading("7 Próximos passos recomendados", level=1)
    add_table(
        doc,
        ["Prioridade", "Ação", "Por que fazer"],
        [
            ["1", "Adicionar contagens reais por aproximação e faixa horária; calibrar as taxas-base e os multiplicadores do perfil IBGE.", "Transformar a estimativa relativa em uma hipótese verificável para o local."],
            ["2", "Repetir a comparação com pelo menos 100 seeds e três regimes: baixa, média e pico.", "Medir robustez e reduzir o risco de concluir por um único cenário."],
            ["3", "Comparar também com um ciclo fixo otimizado e com variações de mínimo/máximo de verde.", "Evitar que o baseline fixo seja penalizado apenas por uma configuração não ajustada."],
            ["4", "Integrar a geometria OSM ao motor ou importar a rede para um simulador microscópico.", "Aproximar a dinâmica do cruzamento real sem perder a reprodutibilidade."],
            ["5", "Adicionar pedestres, ciclistas e prioridade de emergência com métricas de segurança.", "Ampliar a validade do controlador para mobilidade multimodal."],
        ],
        [0.7, 3.5, 2.7],
    )

    doc.add_heading("8 Reprodutibilidade", level=1)
    add_body(doc, "Os principais comandos executados para gerar os artefatos foram:")
    commands = [
        "python -m sergipe_traffic_ai.data_pipeline.checkin2 --fetch-geography --fetch-osm",
        "python experiments/train_q_learning.py",
        "python experiments/compare_controllers.py --seeds 20 --seed-start 1000 --duration 600",
        "python tools/create_report_figures.py",
    ]
    for command in commands:
        paragraph = doc.add_paragraph(style="List Bullet")
        run = paragraph.add_run(command)
        set_run_font(run, name="Consolas", size=9.2, color="333333")
    add_body(doc, "Os resultados brutos ficam no repositório em experiments/output/checkin2, experiments/output/comparison e experiments/output/report. O modelo treinado é salvo em models/q_learning_aracaju.json. A comparação final usa as mesmas seeds para os três controladores.")

    doc.add_heading("9 Fontes e créditos", level=1)
    add_body(doc, "Fontes oficiais e licenças utilizadas no projeto:")
    add_source_link(doc, "IBGE Cidades e Estados — Aracaju", "https://www.ibge.gov.br/cidades-e-estados/se/aracaju.html")
    add_source_link(doc, "IBGE Cidades e Estados — Sergipe", "https://www.ibge.gov.br/cidades-e-estados/se.html")
    add_source_link(doc, "IBGE Malhas — Sergipe", "https://servicodados.ibge.gov.br/api/v3/malhas/estados/28?formato=application/vnd.geo+json&qualidade=minima")
    add_source_link(doc, "IBGE Malhas — Aracaju", "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/2800308?formato=application/vnd.geo+json&qualidade=minima")
    add_source_link(doc, "OpenStreetMap — direitos autorais e licença", "https://www.openstreetmap.org/copyright")
    add_source_link(doc, "OpenStreetMap Wiki — Overpass API", "https://wiki.openstreetmap.org/wiki/Overpass_API")
    add_body(doc, "Atribuição cartográfica: © OpenStreetMap contributors. Os dados do OpenStreetMap são distribuídos sob a ODbL 1.0. O IBGE é a fonte dos recortes territoriais e indicadores demográficos usados no contexto e na estimativa relativa da demanda. A rede viária foi consultada em 14 de novembro de 2026; os dados OSM podem mudar com novas edições.")

    doc.add_page_break()
    doc.add_heading("10 Checklist de encerramento do projeto", level=1)
    add_table(
        doc,
        ["Item", "Situação"],
        [
            ["Integração OSM via Overpass API", "Concluída; GeoJSON processado e mapa contextual gerado."],
            ["Integração IBGE", "Concluída; malhas de Sergipe e Aracaju validadas, indicadores demográficos incorporados à estimativa de demanda e perfil horário aplicado."],
            ["Controlador fixo", "Implementado e usado como baseline."],
            ["Controlador adaptativo", "Implementado como heurística dinâmica sem aprendizado."],
            ["Q-learning", "Treinado, salvo em JSON e avaliado sem exploração."],
            ["Comparação controlada", "Concluída em 20 seeds pareadas; Q-learning liderou espera/fila e adaptativo liderou throughput."],
            ["Próxima versão acadêmica", "Calibração com contagens reais, mais cenários e mobilidade multimodal."],
        ],
        [2.2, 4.7],
    )

    doc.core_properties.title = "Relatório de validação do Sergipe Traffic AI"
    doc.core_properties.subject = "OpenStreetMap, IBGE e comparação de controladores semafóricos"
    doc.core_properties.author = "Sergipe Traffic AI"
    doc.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(build_report())
