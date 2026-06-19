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
        out += f'<div style="text-align:center;"><div style="width:28px;height:28px;border-radius:50%;background:{bg};{bd}color:{tc};font-size:8.5px;font-weight:bold;line-height:28px;margin:0 auto;">{gr}</div>{badge}</div>'
    return out

def build_precio_html(data):
    pmode = data.get('pmode', 'liq')
    html = ""

    if pmode == 'liq':
        monto = data.get('p_liq', '')
        limite = data.get('p_liq_limite_txt', '')
        html = f"""
        <div style="display:flex;gap:12px;margin:0 36px;">
          <div style="flex:1;background:linear-gradient(110deg,{PINK},#C13760);border-radius:8px;padding:13px 16px;color:#fff;">
            <div style="font-size:8px;font-weight:bold;letter-spacing:.8px;opacity:.92;">LIQUIDACIÓN DE CONTADO</div>
            <div style="font-size:28px;font-weight:bold;margin:4px 0;">{fmt_money(monto)} <span style="font-size:12px;font-weight:normal;">MXN</span></div>
            <div style="font-size:8px;opacity:.93;">Pago único — el mejor precio disponible</div>
            {f'<div style="margin-top:6px;background:rgba(255,255,255,.2);border-radius:5px;padding:5px 9px;font-size:8px;">⏰ Liquidando antes del {limite}</div>' if limite else ''}
          </div>
        </div>"""

    elif pmode == 'hit':
        h_meses = int(data.get('h_meses', 0))
        costo_map = {3: 60000, 6: 63000, 9: 67000, 12: 70000}
        tot = costo_map.get(h_meses, 0)
        mitad = tot // 2
        mens = -(-mitad // h_meses) if h_meses else 0
        html = f"""
        <div style="margin:0 36px;">
          <div style="background:linear-gradient(110deg,{PURPLE},{NAVY});color:#fff;border-radius:8px;padding:10px 16px;margin-bottom:10px;">
            <div style="font-size:9px;font-weight:bold;letter-spacing:.5px;">PLAN ACCESO INMEDIATO</div>
            <div style="font-size:11px;opacity:.85;margin-top:2px;">50% para ingresar a sala · 50% diferido en {h_meses} mensualidades</div>
          </div>
          <div style="display:flex;gap:10px;">
            <div style="flex:1;background:#fdeef4;border-top:4px solid {PINK};border-radius:7px;padding:12px;text-align:center;">
              <div style="font-size:8px;font-weight:bold;color:{PINK};letter-spacing:.5px;margin-bottom:4px;">INGRESO A SALA</div>
              <div style="font-size:22px;font-weight:bold;color:{PINK};">{fmt_money(mitad)}</div>
              <div style="font-size:8px;color:{PINK};margin-top:2px;">50% del costo total</div>
            </div>
            <div style="flex:1;background:{LP};border-top:4px solid {PURPLE};border-radius:7px;padding:12px;text-align:center;">
              <div style="font-size:8px;font-weight:bold;color:{PURPLE};letter-spacing:.5px;margin-bottom:4px;">SALDO DIFERIDO</div>
              <div style="font-size:22px;font-weight:bold;color:{PURPLE};">{fmt_money(mitad)}</div>
              <div style="font-size:8px;color:{PURPLE};margin-top:2px;">50% en {h_meses} mensualidades</div>
            </div>
            <div style="flex:1;background:#eafaf6;border-top:4px solid {TEAL};border-radius:7px;padding:12px;text-align:center;">
              <div style="font-size:8px;font-weight:bold;color:#0F6E56;letter-spacing:.5px;margin-bottom:4px;">MENSUALIDAD</div>
              <div style="font-size:22px;font-weight:bold;color:#0F6E56;">{fmt_money(mens)}</div>
              <div style="font-size:8px;color:#0F6E56;margin-top:2px;">por {h_meses} meses</div>
            </div>
          </div>
        </div>"""

    elif pmode == 'fin':
        ini = int(data.get('p_finicial', 0) or 0)
        mes = int(data.get('p_fmeses', 0) or 0)
        pai_map = {6: 63000, 9: 67000, 12: 70000}
        pai_base = pai_map.get(mes, 70000)
        ini_pai = pai_base / 2
        if ini >= ini_pai:
            tot = pai_base
        else:
            deficit = (ini_pai - ini) / ini_pai
            inc = round(deficit * 12000 / 1000) * 1000
            tot = min(pai_base + inc, 75000)
        saldo = tot - ini
        mens = -(-saldo // mes) if mes else 0
        mes_acceso = -(-mes * 7 // 10)
        html = f"""
        <div style="margin:0 36px;">
          <div style="background:linear-gradient(110deg,{PURPLE},{NAVY});color:#fff;border-radius:8px;padding:10px 16px;margin-bottom:10px;">
            <div style="font-size:9px;font-weight:bold;letter-spacing:.5px;">FINANCIAMIENTO INTERNO</div>
            <div style="font-size:11px;opacity:.85;margin-top:2px;">Pago inicial personalizado + {mes} mensualidades</div>
          </div>
          <div style="display:flex;gap:10px;margin-bottom:10px;">
            <div style="flex:1;background:{LP};border-top:4px solid {PURPLE};border-radius:7px;padding:12px;text-align:center;">
              <div style="font-size:8px;font-weight:bold;color:{PURPLE};letter-spacing:.5px;margin-bottom:4px;">COSTO TOTAL</div>
              <div style="font-size:20px;font-weight:bold;color:{PURPLE};">{fmt_money(tot)}</div>
            </div>
            <div style="flex:1;background:#fdeef4;border-top:4px solid {PINK};border-radius:7px;padding:12px;text-align:center;">
              <div style="font-size:8px;font-weight:bold;color:{PINK};letter-spacing:.5px;margin-bottom:4px;">PAGO INICIAL</div>
              <div style="font-size:20px;font-weight:bold;color:{PINK};">{fmt_money(ini)}</div>
            </div>
            <div style="flex:1;background:#eafaf6;border-top:4px solid {TEAL};border-radius:7px;padding:12px;text-align:center;">
              <div style="font-size:8px;font-weight:bold;color:#0F6E56;letter-spacing:.5px;margin-bottom:4px;">MENSUALIDAD</div>
              <div style="font-size:20px;font-weight:bold;color:#0F6E56;">{fmt_money(mens)}</div>
            </div>
          </div>
          <div style="background:{LP};border-left:4px solid {PURPLE};border-radius:6px;padding:9px 14px;font-size:8.5px;color:#3a2a5a;line-height:1.5;">
            Al liquidar el <strong>70% de los pagos de forma puntual</strong> el día 15 de cada mes, el paciente tiene el <strong>acceso garantizado a sala en el mes {mes_acceso}</strong>.
          </div>
        </div>"""

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
    lista_precio = n_zonas * 75000

    HEAD = f'''
    <div style="background:{NAVY};padding:18px 36px;display:flex;justify-content:space-between;align-items:center;">
      <img src="data:image/png;base64,{LOGO_B64}" style="height:52px;">
      <div style="text-align:right;color:#D8D6E6;font-size:8px;line-height:1.5;">
        <div style="color:#fff;font-size:11px;font-weight:bold;">800 999 01 22</div>
        administracion@cabelix.com · www.cabelix.com<br>
        Av. Eugenio Garza Sada 3820, Mas Palomas, 64780 Monterrey, N.L.
      </div>
    </div>
    <div style="background:{PURPLE};color:#fff;font-size:8px;padding:5px 36px;display:flex;justify-content:space-between;">
      <span>Documento oficial · No requiere firma para ser válido</span>
      <span>Válida 7 días a partir de la fecha de emisión</span>
    </div>'''

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
            <div style="flex:1;">
              <div style="border:2px solid {PURPLE};border-radius:8px;overflow:hidden;background:#f4f3f8;height:160px;display:flex;align-items:center;justify-content:center;">
                <img src="data:image/jpeg;base64,{f64}" style="max-width:100%;max-height:100%;object-fit:contain;">
              </div>
              <div style="text-align:center;font-size:7px;color:{PURPLE};font-style:italic;margin-top:4px;">{label}</div>
            </div>''')
        fotos_html = f'<div style="display:flex;gap:10px;margin-top:6px;">{"".join(cols)}</div>'

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
      <div style="padding:16px 36px 10px;display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1px solid #e0dde8;">
        <div>
          <h1 style="font-size:21px;color:{NAVY};letter-spacing:1px;">{titulo}</h1>
          <div style="font-size:8.5px;color:#6A6A85;margin-top:3px;">{fecha_str} · Nunca serás tan joven como hoy</div>
        </div>
        <div style="font-size:19px;color:{PURPLE};font-weight:bold;">{folio}</div>
      </div>

      <div style="background:{LP};border-left:5px solid {PURPLE};margin:14px 36px;padding:10px 16px;display:flex;gap:28px;font-size:9.5px;">
        <div><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:2px;">PACIENTE</b>{nombre}</div>
        <div><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:2px;">FECHA DE VALORACIÓN</b>{fecha_str}</div>
        <div><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:2px;">SUCURSAL</b>{sucursal}</div>
        <div><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:2px;">CONSULTOR</b>{realizado}</div>
      </div>

      <div style="padding:0 36px;">
        <div style="display:flex;gap:18px;">
          <div style="flex:1.3;background:{LP};border-radius:8px;padding:13px 16px;">
            <div style="color:{PURPLE};font-size:7.5px;font-weight:bold;letter-spacing:1px;margin-bottom:6px;">
              DIAGNÓSTICO CLÍNICO{f" · GRADO {norwood_g}" if norwood_g else ""} · {', '.join(zonas) if zonas else servicio.upper()}
            </div>
            <p style="font-size:8.5px;line-height:1.5;text-align:justify;color:#3a3a4a;white-space:pre-line;">{diagnostico}</p>
            {f'<div style="margin-top:8px;font-size:7.5px;color:#6A6A85;"><strong>Zona donante:</strong> {zona_don_str}</div>' if zona_don_str else ''}
          </div>
          {f'''<div style="flex:1;">
            <div style="color:{PURPLE};font-size:7.5px;font-weight:bold;letter-spacing:1px;margin-bottom:8px;text-align:center;">ESCALA NORWOOD-HAMILTON</div>
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">{norwood_widget(norwood_g)}</div>
          </div>''' if norwood_g and servicio == 'microinjerto' else ''}
        </div>

        {f'<div style="font-size:8px;color:{PURPLE};font-weight:bold;letter-spacing:1px;margin:14px 0 6px;">REGISTRO FOTOGRÁFICO</div>{fotos_html}' if fotos else ''}
      </div>

      <div style="display:flex;gap:14px;padding:0 36px;margin-top:14px;">
        <div style="flex:1;background:{LP};border-top:4px solid {PURPLE};border-radius:6px;padding:12px 14px;">
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
        </div>
        <div style="flex:1;background:{LP};border-top:4px solid {PURPLE};border-radius:6px;padding:12px 14px;">
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
        </div>
      </div>
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
      <div style="padding:16px 36px 10px;display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1px solid #e0dde8;">
        <div>
          <h1 style="font-size:21px;color:{NAVY};letter-spacing:1px;">PROPUESTA ECONÓMICA</h1>
          <div style="font-size:8.5px;color:#6A6A85;margin-top:3px;">{fecha_str}</div>
        </div>
        <div style="font-size:19px;color:{PURPLE};font-weight:bold;">{folio}</div>
      </div>
      <div style="background:{LP};border-left:5px solid {PURPLE};margin:14px 36px;padding:10px 16px;display:flex;gap:28px;font-size:9.5px;">
        <div><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:2px;">PACIENTE</b>{nombre}</div>
        <div><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:2px;">FOLIO</b>{folio}</div>
        <div><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:2px;">ZONAS</b>{', '.join(zonas) if zonas else '—'}</div>
        <div><b style="color:{PURPLE};display:block;font-size:7.5px;letter-spacing:.5px;margin-bottom:2px;">PRECIO DE LISTA</b>${lista_precio:,} MXN</div>
      </div>
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
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'ok', 'mensaje': 'Cabelix PDF backend activo'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
