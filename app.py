import os
from datetime import datetime
from itertools import zip_longest
from urllib.parse import quote
from flask import Flask, render_template, request, redirect, url_for, flash, Response

import database
from pricing import calcular_precio

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-only-change-me')

# === Config del negocio (puedes cambiarlos o usar variables de entorno) ===
WHATSAPP_NUMBER = os.getenv("LAVA_WHATSAPP", "51999999999")  # <-- cambia por tu número
LAVA_DIRECCION = os.getenv("LAVA_DIRECCION", "Tu calle #123, Huánuco")
PROMO_BANNER   = os.getenv("LAVA_PROMO", "🌿 Martes: perfumado GRATIS en lavados por kilo")

# Inicializar BD
database.crear_bd()

# Inyectar datos globales a los templates
@app.context_processor
def inject_globals():
    return dict(
        WHATSAPP_NUMBER=WHATSAPP_NUMBER,
        LAVA_DIRECCION=LAVA_DIRECCION,
        PROMO_BANNER=PROMO_BANNER
    )

# ------------------- PÁGINAS BASE -------------------
@app.route("/")
def home():
    return render_template("index.html")



@app.route("/boletas")
def boletas():
    pagina = int(request.args.get("page", 1))
    limite = 20
    offset = (pagina - 1) * limite

    cliente = (request.args.get("cliente") or "").strip() or None
    fecha_desde = request.args.get("desde") or None
    fecha_hasta = request.args.get("hasta") or None

    filas = database.obtener_boletas_paginado(
        limit=limite, offset=offset, cliente=cliente,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
    )
    total_registros = database.contar_boletas(cliente=cliente, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    total_paginas = max(1, (total_registros + limite - 1) // limite)
    total_periodo = database.total_periodo(cliente=cliente, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)

    return render_template(
        "boletas.html", filas=filas, pagina=pagina, total_paginas=total_paginas,
        total_periodo=total_periodo,
        filtros={"cliente": cliente or "", "desde": fecha_desde or "", "hasta": fecha_hasta or ""},
    )

@app.route("/export.csv")
def export_csv():
    POTENTIALLY_DANGEROUS = ("=", "+", "-", "@")
    def sanitize_cell(s):
        s = str(s or "")
        return ("'" + s) if (s and s[0] in POTENTIALLY_DANGEROUS) else s

    import csv, io
    filas = database.obtener_boletas_todas()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)

    writer.writerow([
        "ID","Fecha","Cliente","Tipo","Kilos","Cantidad","Servicio",
        "Perfumado","Método de pago","Estado","Precio"
    ])
    for b in filas:
        (id_, cliente, tipo_item, kilos, cantidad, servicio, perfumado, precio, fecha, metodo_pago, estado) = b
        writer.writerow([
            id_, fecha, sanitize_cell(cliente), tipo_item, kilos, cantidad, servicio,
            "Sí" if perfumado == 1 else "No", metodo_pago, estado, f"{float(precio):.2f}"
        ])

    filename = f"boletas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(), mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route('/logout')
def logout():
    flash('Sesión cerrada (demo).', 'info')
    return redirect(url_for('home'))

# ------------------- NUEVO: BOLETA MULTI-ITEM -------------------
def _normalize_phone(raw: str|None) -> str|None:
    if not raw: return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits: return None
    if not digits.startswith("51"):
        digits = "51" + digits.lstrip("0")
    return digits

@app.route("/boleta/nueva", methods=["GET", "POST"])
def boleta_nueva():
    if request.method == "POST":
        try:
            # Helpers
            def to_float(x, default=0.0):
                try: return float((x or "").replace(",", "."))
                except: return default
            def to_int(x, default=0):
                try: return int(float(x or 0))
                except: return default

            # Cabecera
            cliente = (request.form.get("cliente") or "").strip()
            direccion = (request.form.get("direccion") or "").strip()
            telefono = (request.form.get("telefono") or "").strip()
            entrega_fecha = request.form.get("entrega_fecha") or ""
            entrega_hora = request.form.get("entrega_hora") or ""
            metodo_pago = request.form.get("metodo_pago") or "efectivo"
            a_cuenta = to_float(request.form.get("a_cuenta"), 0.0)
            notas = (request.form.get("notas") or "").strip()

            if not cliente:
                flash("El nombre del cliente es obligatorio", "error")
                return render_template("boleta_nueva.html")

            # Ítems (listas)
            tipos   = request.form.getlist("item_tipo[]")
            descs   = request.form.getlist("item_desc[]")
            cantidades = request.form.getlist("item_cantidad[]")
            lavados = request.form.getlist("item_lavado[]")
            perfumados = request.form.getlist("item_perfumado[]")
            perfumados_hidden = request.form.getlist("item_perfumado_hidden[]")
            punits  = request.form.getlist("item_punit[]")

            items, total = [], 0.0
            for t, d, cnt, lv, pf, pfh, pu in zip_longest(
                tipos, descs, cantidades, lavados, perfumados, perfumados_hidden, punits, fillvalue=""
            ):
                t = (t or "").strip()
                d = (d or "").strip()
                cnt_v = to_float(cnt, 1.0)
                pu_v = to_float(pu, 0.0)
                lv = (lv or "Normal").strip()

                # Saltar filas vacías
                if not t and pu_v == 0 and cnt_v == 0:
                    continue
                if not t: t = "kilo"
                if not d: d = t.capitalize()

                # Importe
                importe = round(cnt_v * pu_v, 2)

                total += importe
                items.append(dict(
                    descripcion=d, tipo=t, cantidad=cnt_v,  # cantidad se usará para prendas o kilos según el tipo
                    lavado=lv, perfumado=1 if pf == "1" else 0, p_unit=pu_v, importe=importe
                ))

            if not items:
                flash("Agrega al menos un ítem con cantidad/precio.", "error")
                return render_template("boleta_nueva.html")

            saldo = round(total - a_cuenta, 2)
            fecha_emision = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cabecera = dict(
                numero=None, cliente=cliente, direccion=direccion, telefono=telefono,
                fecha=fecha_emision, entrega_fecha=entrega_fecha, entrega_hora=entrega_hora,
                metodo_pago=metodo_pago, estado="registrado",
                a_cuenta=a_cuenta, saldo=saldo, total=round(total, 2), notas=notas
            )

            # Guardar en nuevo esquema (cabecera + items)
            boleta_id = database.insertar_boleta_compuesta(cabecera, items)

            # ===== Compatibilidad: UNA SOLA LÍNEA en 'boletas' (resumen consolidado) =====
            sum_kilos, sum_unidades = 0.0, 0
            for it in items:
                t = it["tipo"]
                if t == "kilo":
                    sum_kilos += float(it["cantidad"] or 0)
                else:
                    sum_unidades += int(it["cantidad"] or 0)

            partes = []
            if sum_kilos > 0: partes.append(f"{sum_kilos:.2f} kg")
            if sum_unidades > 0: partes.append(f"{sum_unidades} unidad(es)")
            tipo_item_resumen = "multi: " + ", ".join(partes) if partes else "multi"

            # Calcular si hay al menos un ítem perfumado
            tiene_perfumado = any(item["perfumado"] == 1 for item in items)
            
            database.insertar_boleta(
                cliente=cliente,
                tipo_item=tipo_item_resumen,
                cantidad=sum_kilos + sum_unidades,
                lavado="mixto",
                perfumado=1 if tiene_perfumado else 0,
                precio=total,
                metodo_pago=metodo_pago,
                estado="registrado",
                fecha=fecha_emision,
            )

            # WhatsApp: al cliente si escribió teléfono, si no al número del negocio
            wa_destino = _normalize_phone(telefono) or WHATSAPP_NUMBER
            msg = (
                f"Hola {cliente}, gracias por elegir Lavandería RÍOS.%0A"
                f"Total: S/ {total:.2f}. A cuenta: S/ {a_cuenta:.2f}. Saldo: S/ {saldo:.2f}.%0A"
                f"Entrega: {entrega_fecha or '-'} {entrega_hora or ''}.%0A"
                f"Dirección: {(direccion or LAVA_DIRECCION)}.%0A"
                f"Detalle:%0A" + "%0A".join([f"• {it['descripcion']} {'(✨ Perfumado)' if it['perfumado'] else ''} — S/ {it['importe']:.2f}" for it in items])
            )
            wa_link = f"https://wa.me/{wa_destino}?text={quote(msg)}"

            flash("Boleta creada con éxito", "success")
            return redirect(url_for("boleta_detalle", boleta_id=boleta_id, wa=wa_link))

        except Exception as e:
            flash(f"Ocurrió un error: {e}", "error")
            return render_template("boleta_nueva.html")

    # GET
    return render_template("boleta_nueva.html")

@app.route("/boleta/<int:boleta_id>")
def boleta_detalle(boleta_id):
    # Obtener la cabecera y los items de la boleta
    cab, items = database.obtener_boleta_detalle(boleta_id)
    
    # Generar el enlace para WhatsApp con los datos de la boleta
    wa_link = request.args.get("wa")  # opcional, pasa por query string
    return render_template("boleta_detalle.html", cab=cab, items=items, wa_link=wa_link)


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug)
