# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from weasyprint import HTML
import os, io, base64, json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Cargar logo
LOGO_B64 = open(os.path.join(os.path.dirname(__file__), 'logo_b64.txt')).read().strip()

# Colores Cabelix
NAVY   = "#1A1A2E"
PURPLE = "#5B3A8A"
TEAL   = "#4EC5B1"
GOLD   = "#C89860"
PINK   = "#EC5D8A"
LP     = "#F5F2FA"

MESES_ES = ['enero','febrero','marzo','abril','mayo','junio',
            'julio','agosto','septiembre','octubre','noviembre','diciembre']

def fmt_fecha(fecha_str):
    try:
        d = datetime.strptime(fecha_str, '%Y-%m-%d')
        return f"{d.day} de {MESES_ES[d.month-1]} de {d.year}"
    except:
        return fecha_str or ''

def fmt_money(val):
    try:
        return f"${int(val):,}".replace(',', ',')
    except:
        return f"${val}"

def norwood_widget(grado_activo):
    grados = ["I","II","III","IV","V","VI","VII"]
    out = ""
    for gr in grados:
        active = (gr == grado_activo)
        bg = PURPLE if active else "#d8d3e6"
        tc = "#fff" if active else "#6A6A85"
        bd = f"border:3px solid {PURPLE};" if active else "border:2px solid #d8d3e6;"
        badge = f'<div style="margin-top:4px;font-size:6.5px;background:{PURPLE};color:#fff;border-radius:8px;padding:1px 5px;font-weight:bold;">Tu caso</div>' if active else '<div style="height:13px;"></div>'
        out += f'<td style="text-align:center;vertical-align:top;"><div style="width:28px;height:28px;border-radius:50%;background:{bg};{bd}color:{tc};font-size:8.5px;font-weight:bold;line-height:28px;margin:0 auto;">{gr}</div>{badge}</td>'
    return out

def build_precio_html(data):
    # ===== LOS 3 PLANES JUNTOS (diseño aprobado por Dr. Julio) =====
    # Las fórmulas validadas se escalan según el precio base por zonas:
    #   1 zona = $75,000  ·  2 zonas = $100,000  ·  3 zonas = $150,000
    # (Dr. Julio: NO se multiplica directo; son montos base fijos por # de zonas)

    # ===== TABLAS EXACTAS DE DR. JULIO (documento oficial junio 2026) =====
    # Estas tablas son los valores oficiales. NO se calculan por factor:
    # se leen directo de la tabla que entregó Dr. Julio, para que el PDF
    # muestre exactamente sus números.

    n_zonas = len(data.get('zonas', [])) or 1
    bht = bool(data.get('bht', False))

    # Clave de fila según zonas + BHT (ej: "1", "1b", "2", "2b", "3", "3b")
    fila = f"{n_zonas}{'b' if bht else ''}"

    # --- Precio de lista (techo) ---
    lista_map = {
        '1': 75000,  '1b': 105000,
        '2': 100000, '2b': 130000,
        '3': 150000, '3b': 180000,
    }
    precio_base = lista_map.get(fila, 75000)

    # --- Plan 1: LIQUIDACIÓN (el consultor escribe el monto a mano) ---
    liq_monto  = data.get('p_liq', '')
    liq_limite = data.get('p_liq_limite_txt', '')

    # --- Plan 2: ACCESO INMEDIATO — Tabla oficial (plazos 3, 6, 9, 12) ---
    # Filas: zonas (+b si BHT). Columnas: meses.
    acceso_tabla = {
        '1':  {3: 60000,  6: 63000,  9: 67000,  12: 70000},
        '1b': {3: 84000,  6: 88000,  9: 94000,  12: 98000},
        '2':  {3: 80000,  6: 84000,  9: 89000,  12: 93000},
        '2b': {3: 104000, 6: 109000, 9: 116000, 12: 121000},
        '3':  {3: 120000, 6: 126000, 9: 134000, 12: 140000},
        '3b': {3: 150000, 6: 156000, 9: 164000, 12: 170000},
    }
    h_meses   = int(data.get('h_meses', 0) or 0)
    hit_tot   = acceso_tabla.get(fila, acceso_tabla['1']).get(h_meses, 0)
    hit_mitad = hit_tot // 2
    hit_mens  = -(-hit_mitad // h_meses) if h_meses else 0

    # --- Plan 3: FINANCIAMIENTO INTERNO — Tabla oficial (plazos 6, 9, 12, 18) ---
    fin_tabla = {
        '1':  {6: 63000,  9: 67000,  12: 70000,  18: 75000},
        '1b': {6: 88000,  9: 94000,  12: 98000,  18: 105000},
        '2':  {6: 84000,  9: 89000,  12: 93000,  18: 100000},
        '2b': {6: 109000, 9: 116000, 12: 121000, 18: 130000},
        '3':  {6: 126000, 9: 134000, 12: 140000, 18: 150000},
        '3b': {6: 156000, 9: 164000, 12: 170000, 18: 180000},
    }
    fin_ini = int(data.get('p_finicial', 0) or 0)
    fin_mes = int(data.get('p_fmeses', 0) or 0)
    fin_tot = fin_tabla.get(fila, fin_tabla['1']).get(fin_mes, 0)
    # Regla Dr. Julio: si el inicial >= 50% del costo del PAI al mismo plazo,
    # el costo del Financiamiento es idéntico al Plan Acceso Inmediato.
    pai_mismo_plazo = acceso_tabla.get(fila, acceso_tabla['1']).get(fin_mes)
    if pai_mismo_plazo and fin_ini >= pai_mismo_plazo / 2:
        fin_tot = pai_mismo_plazo
    fin_saldo = fin_tot - fin_ini
    fin_mens = -(-fin_saldo // fin_mes) if fin_mes else 0
    fin_mes_acceso = -(-fin_mes * 7 // 10) if fin_mes else 0

    # ---- CAJA 1: LIQUIDACIÓN (verde) ----
    liq_card = f"""
      <td style="width:33.33%;padding:0 5px;vertical-align:top;">
        <div style="background:#0F3D33;border-radius:9px;padding:13px;color:#fff;min-height:160px;">
          <div style="font-size:7px;font-weight:bold;letter-spacing:.8px;color:#6fe3cb;margin-bottom:3px;">LIQUIDACIÓN</div>
          <div style="font-size:11px;font-weight:bold;color:#fff;margin-bottom:7px;">Pago de contado</div>
          <div style="font-size:28px;font-weight:bold;color:{TEAL};line-height:1;margin:4px 0 8px;">{fmt_money(liq_monto)}</div>
          <div style="font-size:7.5px;color:#b8e8df;line-height:1.5;">Pago único — el mejor precio disponible
          {f'<br>⏰ Liquidando antes del <b style="color:#fff;">{liq_limite}</b>' if liq_limite else ''}</div>
        </div>
      </td>"""

    # ---- CAJA 2: FINANCIAMIENTO (borde morado) ----
    fin_card = f"""
      <td style="width:33.33%;padding:0 5px;vertical-align:top;">
        <div style="background:#fff;border:2px solid {PURPLE};border-radius:9px;padding:13px;min-height:160px;">
          <div style="font-size:7px;font-weight:bold;letter-spacing:.8px;color:{PURPLE};margin-bottom:3px;">FINANCIAMIENTO INTERNO</div>
          <div style="font-size:11px;font-weight:bold;color:{NAVY};margin-bottom:6px;">Costo total {fmt_money(fin_tot)}</div>
          <div style="font-size:24px;font-weight:bold;color:{PURPLE};line-height:1;margin:3px 0 7px;">{fmt_money(fin_ini)} <span style="font-size:9px;color:#6A6A85;">inicial</span></div>
          <div style="border-top:1px dashed #d6cfe6;padding-top:6px;margin-top:4px;font-size:8.5px;color:#3a3a4a;">
            {fin_mes} mensualidades de <b style="color:{PURPLE};">{fmt_money(fin_mens)}</b>
          </div>
          <div style="background:{TEAL};color:#08423a;font-size:7px;font-weight:bold;border-radius:5px;padding:4px 7px;margin-top:7px;text-align:center;">
            ACCESO A SALA CON 70% LIQUIDADO (MES {fin_mes_acceso})
          </div>
        </div>
      </td>"""

    # ---- CAJA 3: PLAN DE ACCESO INMEDIATO (morado sólido) ----
    hit_card = f"""
      <td style="width:33.33%;padding:0 5px;vertical-align:top;">
        <div style="background:{PURPLE};border-radius:9px;padding:13px;color:#fff;min-height:160px;">
          <div style="font-size:7px;font-weight:bold;letter-spacing:.8px;color:#cdbdf0;margin-bottom:3px;">PLAN DE ACCESO INMEDIATO</div>
          <div style="font-size:11px;font-weight:bold;color:#fff;margin-bottom:6px;">Liquidas 50% y entras a sala</div>
          <div style="font-size:21px;font-weight:bold;color:#fff;line-height:1.05;margin:4px 0 6px;">{fmt_money(hit_mitad)} <span style="font-size:11px;">+ {fmt_money(hit_mitad)}</span></div>
          <div style="font-size:8px;color:#e6dcfa;line-height:1.6;">
            <b style="color:#fff;">Liquidas el 50%</b> e ingresas a sala<br>
            El otro 50% en {h_meses} mensualidades<br>de <b style="color:#fff;">{fmt_money(hit_mens)}</b> cada una
          </div>
          <div style="background:{PINK};color:#fff;font-size:7px;font-weight:bold;border-radius:5px;padding:4px 7px;margin-top:7px;text-align:center;">
            INGRESO INMEDIATO A SALA
          </div>
        </div>
      </td>"""

    html = f"""
    <table style="margin:14px 36px 0;width:calc(100% - 72px);border-collapse:collapse;">
      <tr>{liq_card}{fin_card}{hit_card}</tr>
    </table>"""

    return html


def build_condiciones_html(data):
    fecha_val = data.get('fecha_val', '')
    try:
        d = datetime.strptime(fecha_val, '%Y-%m-%d')
        vig = d + timedelta(days=7)
        vig_str = fmt_fecha(vig.strftime('%Y-%m-%d'))
    except:
        vig_str = "7 días a partir de la fecha de emisión"

    fecha_proc = data.get('fecha_proc', '')
    fecha_proc_html = f'<li>Fecha tentativa de procedimiento: <strong>{fmt_fecha(fecha_proc)}</strong>.</li>' if fecha_proc else ''

    notas = data.get('notas_consultor', '')
    notas_html = f'<li><strong>Nota del consultor:</strong> {notas}</li>' if notas else ''

    return f"""
    <div style="margin:10px 36px 0;background:{PURPLE};border-radius:8px;padding:11px 16px;">
      <h3 style="color:#fff;font-size:8.5px;letter-spacing:.5px;margin-bottom:6px;">CONDICIONES IMPORTANTES</h3>
      <ul style="list-style:none;">
        {''.join([f'<li style="font-size:7.5px;color:#e8e3f2;line-height:1.45;padding-left:13px;position:relative;margin-bottom:3px;"><span style="color:{TEAL};position:absolute;left:0;">▸</span>{c}</li>' for c in [
          'Esta cotización tiene una vigencia de 7 días naturales a partir de la fecha de emisión.',
          'El anticipo para apartar fecha no es reembolsable con menos de 72 horas de anticipación.',
          'El procedimiento de microinjerto FUE/DHI es ambulatorio bajo anestesia local, sin hospitalización.',
          'Los resultados son progresivos e individuales. Visibles desde el mes 6, definitivos al mes 12.',
          'El plan de financiamiento interno requiere firma de pagaré y está sujeto a aprobación interna.',
          'Esta cotización es personal e intransferible y corresponde exclusivamente al paciente indicado.',
        ]])}
        {f'<li style="font-size:7.5px;color:#e8e3f2;line-height:1.45;padding-left:13px;position:relative;margin-bottom:3px;"><span style="color:{TEAL};position:absolute;left:0;">▸</span>Fecha tentativa de procedimiento: <strong>{fmt_fecha(fecha_proc)}</strong>.</li>' if fecha_proc else ''}
        {f'<li style="font-size:7.5px;color:#e8e3f2;line-height:1.45;padding-left:13px;position:relative;margin-bottom:3px;"><span style="color:{TEAL};position:absolute;left:0;">▸</span><strong>Nota:</strong> {notas}</li>' if notas else ''}
      </ul>
    </div>
    <div style="margin:10px 36px 0;border:2px solid {TEAL};border-radius:8px;background:#f0faf7;text-align:center;padding:8px;font-size:9px;color:{NAVY};">
      VIGENCIA: Esta cotización es válida hasta el <strong>{vig_str}</strong>
    </div>"""

def generar_pdf(data):
    folio       = data.get('folio', '#000000-000')
    nombre      = data.get('nombre', '')
    realizado   = data.get('realizado_por', '')
    fecha_val   = data.get('fecha_val', '')
    sucursal    = data.get('sucursal', '')
    servicio    = data.get('servicio', 'microinjerto')
    norwood_g   = data.get('norwood', '')
    zonas       = data.get('zonas', [])
    zonas_d     = data.get('zonas_donantes', [])
    bht         = data.get('bht', False)
    diagnostico = data.get('diagnostico', '')
    fotos       = data.get('fotos', [])  # lista de base64
    foto_labels = data.get('foto_labels', [])
    promo       = data.get('promo', '')

    fecha_str   = fmt_fecha(fecha_val)
    n_zonas     = len(zonas)
    # Precio de lista oficial (tabla Dr. Julio), con sobrecosto BHT incluido
    fila_lista = f"{n_zonas if n_zonas else 1}{'b' if bht else ''}"
    lista_oficial = {
        '1': 75000,  '1b': 105000,
        '2': 100000, '2b': 130000,
        '3': 150000, '3b': 180000,
    }
    lista_precio = lista_oficial.get(fila_lista, 75000)

    HEAD = f'''
    <table style="background:{NAVY};width:100%;border-collapse:collapse;"><tr>
      <td style="padding:18px 36px;vertical-align:middle;"><img src="data:image/png;base64,{LOGO_B64}" style="height:52px;"></td>
      <td style="padding:18px 36px;text-align:right;color:#D8D6E6;font-size:8px;line-height:1.5;vertical-align:middle;">
        <div style="color:#fff;font-size:11px;font-weight:bold;">800 999 01 22</div>
        administracion@cabelix.com · www.cabelix.com<br>
        Av. Eugenio Garza Sada 3820, Mas Palomas, 64780 Monterrey, N.L.
      </td>
    </tr></table>
    <table style="background:{PURPLE};color:#fff;font-size:8px;width:100%;border-collapse:collapse;"><tr>
      <td style="padding:5px 36px;">Documento oficial · No requiere firma para ser válido</td>
      <td style="padding:5px 36px;text-align:right;">Válida 7 días a partir de la fecha de emisión</td>
    </tr></table>'''

    FOOT = f'''
    <div style="position:absolute;bottom:0;left:0;right:0;">
      <div style="background:{NAVY};color:#cfcde0;font-size:7.5px;text-align:center;padding:7px;letter-spacing:.5px;">
        CABELIX AESTHETICAL MEDICAL CENTER · Microimplante Capilar
      </div>
      <div style="background:{PINK};color:#fff;font-size:7.5px;text-align:center;padding:6px;letter-spacing:1px;font-weight:bold;">
        SUCURSALES: MONTERREY · SALTILLO · ZACATECAS · AGUASCALIENTES · SAN JOSÉ
      </div>
    </div>'''

    # Fotos HTML
    fotos_html = ""
    if fotos:
        cols = []
        for i, f64 in enumerate(fotos[:3]):
            label = foto_labels[i] if i < len(foto_labels) else f"Vista {i+1}"
            cols.append(f'''
            <td style="width:33.33%;padding:0 5px;vertical-align:top;">
              <div style="border:2px solid {PURPLE};border-radius:8px;overflow:hidden;background:#f4f3f8;height:160px;text-align:center;">
                <img src="data:image/jpeg;base64,{f64}" style="max-width:100%;max-height:160px;object-fit:contain;">
              </div>
              <div style="text-align:center;font-size:7px;color:{PURPLE};font-style:italic;margin-top:4px;">{label}</div>
            </td>''')
        fotos_html = f'<table style="width:100%;margin-top:6px;border-collapse:collapse;"><tr>{"".join(cols)}</tr></table>'

    # Zona donante
    zona_don_str = ""
    if zonas_d:
        zona_don_str = ', '.join(zonas_d)
        if bht:
            zona_don_str += ' · BHT activo'

    # Página 1
    titulo = "VALORACIÓN MÉDICA" if servicio == 'microinjerto' else "VALORACIÓN MÉDICA"

    p1 = f'''
    <div class="page">
      {HEAD}
      <table style="width:100%;border-collapse:collapse;border-bottom:1px solid #e0dde8;"><tr>
        <td style="padding:16px 36px 10px;vertical-align:bottom;">
          <h1 style="font-size:21px;color:{NAVY};letter-spacing:1px;">{titulo}</h1>
          <div style="font-size:8.5px;color:#6A6A85;margin-top:3px;">{fecha_str}</div>
        </td>
        <td style="padding:16px 36px 10px;text-align:right;vertical-align:bottom;font-size:19px;color:{PURPLE};font-weight:bold;">{folio}</td>
      </tr></table>

      <table style="background:{LP};border-left:5px solid {PURPLE};margin:14px 36px;width:calc(100% - 72px);border-collapse:collapse;font-size:9.5px;"><tr>
        <td style="padding:10px 16px;vertical-align:top;width:28%;"><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:3px;">PACIENTE</b>{nombre}</td>
        <td style="padding:10px 16px;vertical-align:top;width:27%;"><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:3px;">FECHA DE VALORACIÓN</b>{fecha_str}</td>
        <td style="padding:10px 16px;vertical-align:top;width:20%;"><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:3px;">SUCURSAL</b>{sucursal}</td>
        <td style="padding:10px 16px;vertical-align:top;width:25%;"><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:3px;">CONSULTOR</b>{realizado}</td>
      </tr></table>

      <div style="padding:0 36px;">
        <table style="width:100%;border-collapse:collapse;"><tr>
          <td style="width:60%;vertical-align:top;padding-right:9px;"><div style="background:{LP};border-radius:8px;padding:13px 16px;">
            <div style="color:{PURPLE};font-size:7.5px;font-weight:bold;letter-spacing:1px;margin-bottom:6px;">
              DIAGNÓSTICO CLÍNICO{f" · GRADO {norwood_g}" if norwood_g else ""} · {', '.join(zonas) if zonas else servicio.upper()}
            </div>
            <p style="font-size:8.5px;line-height:1.5;text-align:justify;color:#3a3a4a;white-space:pre-line;">{diagnostico}</p>
            {f'<div style="margin-top:8px;font-size:7.5px;color:#6A6A85;"><strong>Zona donante:</strong> {zona_don_str}</div>' if zona_don_str else ''}
          </div></td>
          {f'''<td style="width:40%;vertical-align:top;padding-left:9px;">
            <div style="color:{PURPLE};font-size:7.5px;font-weight:bold;letter-spacing:1px;margin-bottom:8px;text-align:center;">ESCALA NORWOOD-HAMILTON</div>
            <table style="width:100%;border-collapse:collapse;"><tr>{norwood_widget(norwood_g)}</tr></table>
          </td>''' if norwood_g and servicio == 'microinjerto' else ''}
        </tr></table>

        {f'<div style="font-size:8px;color:{PURPLE};font-weight:bold;letter-spacing:1px;margin:14px 0 6px;">REGISTRO FOTOGRÁFICO</div>{fotos_html}' if fotos else ''}
      </div>

      <table style="width:calc(100% - 72px);margin:14px 36px 0;border-collapse:collapse;"><tr>
        <td style="width:50%;vertical-align:top;padding-right:7px;"><div style="background:{LP};border-top:4px solid {PURPLE};border-radius:6px;padding:12px 14px;">
          <h3 style="font-size:8.5px;color:{NAVY};letter-spacing:.5px;margin-bottom:7px;">PROCEDIMIENTO Y ATENCIÓN</h3>
          <ul style="list-style:none;">
            {''.join([f'<li style="font-size:8px;line-height:1.5;padding-left:14px;position:relative;margin-bottom:4px;color:#3a3a4a;"><span style="color:{TEAL};position:absolute;left:0;font-size:9px;">▸</span>{item}</li>' for item in ([
              f'Microinjerto capilar FUE/DHI · Zonas: {", ".join(zonas)}',
              'Procedimiento ambulatorio en una sola sesión',
              'Extracción folicular e implantación DHI con implanters especializados',
              'Anestesia local, sin hospitalización',
              'Incluye: insumos, honorarios médicos y de enfermería, kit de cuidados y consulta pre-procedimiento',
            ] if servicio == 'microinjerto' else [
              'Mesoterapia capilar: microinyecciones en cuero cabelludo',
              'Activos: dutasteride, péptidos y exosomas',
              'Tratamiento oral complementario: minoxidil',
              'Sin procedimiento quirúrgico ni tiempo de recuperación',
              'Aplicación por personal médico en consultorio',
            ])
            ])}
          </ul>
        </div></td>
        <td style="width:50%;vertical-align:top;padding-left:7px;"><div style="background:{LP};border-top:4px solid {PURPLE};border-radius:6px;padding:12px 14px;">
          <h3 style="font-size:8.5px;color:{NAVY};letter-spacing:.5px;margin-bottom:7px;">RESULTADOS ESPERADOS</h3>
          <ul style="list-style:none;">
            {''.join([f'<li style="font-size:8px;line-height:1.5;padding-left:14px;position:relative;margin-bottom:4px;color:#3a3a4a;"><span style="color:{TEAL};position:absolute;left:0;font-size:9px;">▸</span>{item}</li>' for item in ([
              'Resultado visible a partir del mes 6, definitivo al mes 12',
              'Densidad y naturalidad acordes al diseño de implantación',
              'Resultado individual según respuesta de cada paciente',
              'Seguimiento post-procedimiento incluido',
            ] if servicio == 'microinjerto' else [
              'Freno de la caída y la miniaturización folicular',
              'Aumento progresivo de densidad y grosor del cabello',
              'Mejoría visible estimada hacia el mes 6 del protocolo',
              'Resultado individual según respuesta de cada paciente',
            ])
            ])}
          </ul>
        </div></td>
      </tr></table>
      {FOOT}
    </div>'''

    # Página 2
    precio_html = build_precio_html(data)
    cond_html   = build_condiciones_html(data)
    promo_html  = f'''<div style="background:linear-gradient(110deg,{PINK},#C13760);color:#fff;margin:12px 36px 0;border-radius:8px;padding:9px 18px;">
      <h2 style="font-size:12px;letter-spacing:.5px;">{promo}</h2>
    </div>''' if promo else ''

    p2 = f'''
    <div class="page">
      {HEAD}
      <table style="width:100%;border-collapse:collapse;border-bottom:1px solid #e0dde8;"><tr>
        <td style="padding:16px 36px 10px;vertical-align:bottom;">
          <h1 style="font-size:21px;color:{NAVY};letter-spacing:1px;">PROPUESTA DE TRATAMIENTO</h1>
          <div style="font-size:8.5px;color:#6A6A85;margin-top:3px;">{fecha_str}</div>
        </td>
        <td style="padding:16px 36px 10px;text-align:right;vertical-align:bottom;font-size:19px;color:{PURPLE};font-weight:bold;">{folio}</td>
      </tr></table>
      <table style="background:{LP};border-left:5px solid {PURPLE};margin:14px 36px;width:calc(100% - 72px);border-collapse:collapse;font-size:9.5px;"><tr>
        <td style="padding:10px 16px;vertical-align:top;width:30%;"><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:3px;">PACIENTE</b>{nombre}</td>
        <td style="padding:10px 16px;vertical-align:top;width:22%;"><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:3px;">FOLIO</b>{folio}</td>
        <td style="padding:10px 16px;vertical-align:top;width:23%;"><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:3px;">ZONAS</b>{', '.join(zonas) if zonas else '—'}</td>
        <td style="padding:10px 16px;vertical-align:top;width:25%;"><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:3px;">PRECIO DE LISTA</b><span style="text-decoration:line-through;color:#9a93c0;">${lista_precio:,} MXN</span></td>
      </tr></table>
      {promo_html}
      <div style="margin-top:14px;">{precio_html}</div>
      {cond_html}
      {FOOT}
    </div>'''

    CSS = f"""
    @page {{ size:8.5in 11in; margin:0; }}
    *{{ margin:0;padding:0;box-sizing:border-box;font-family:'Helvetica Neue',Arial,sans-serif; }}
    body{{ color:#2a2a3a; }}
    .page{{ position:relative;width:8.5in;height:11in;padding:0 0 80px 0;overflow:hidden;page-break-after:always; }}
    .page:last-child{{ page-break-after:auto; }}
    """

    html_content = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{p1}{p2}</body></html>"
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


@app.route('/generar', methods=['POST'])
def generar():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Sin datos'}), 400

        pdf_bytes = generar_pdf(data)
        nombre = data.get('nombre', 'cotizacion').replace(' ', '_')
        folio  = data.get('folio', '000').replace('#', '')

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"Cotizacion_{folio}_{nombre}.pdf"
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'ok', 'mensaje': 'Cabelix PDF backend activo'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
