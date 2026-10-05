import os
import requests
import logging
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# السماح بطريقتي POST (لاستقبال أودو) و GET (لتنشيط الرندر وإبقاء الأداة خضراء)
@app.route('/send-invoice', methods=['POST', 'GET'])
def send_invoice():
    # إذا كانت الزيارة من أداة التنشيط بطريقة GET، نرد بنجاح فوري لإبقاء السيرفر مستيقظاً وتجنب خطأ 405
    if request.method == 'GET':
        return jsonify({"status": "active", "message": "Server is awake and running!"}), 200

    try:
        GREEN_API_INSTANCE_ID = (os.environ.get('GREEN_API_INSTANCE_ID') or '').strip()
        GREEN_API_TOKEN = (os.environ.get('GREEN_API_TOKEN') or '').strip()

        data = request.json or {}
        logging.info(f"Received payload from Odoo: {data}")
        
        # استخراج رقم الهاتف
        phone_raw = (
            data.get('x_studio_phone') or 
            data.get('mobile') or 
            data.get('phone') or 
            data.get('x_studio_customer_phone')
        )
        
        if not phone_raw and isinstance(data.get('partner_id'), dict):
            phone_raw = data['partner_id'].get('mobile') or data['partner_id'].get('phone')

        # استخراج حالة الطلب
        status = (
            data.get('x_studio_selection_field_951_1j26vhvop') or 
            data.get('Production_Status') or 
            'غير محدد'
        )
        
        order_name = data.get('name', 'الطلب')

        # نص الرسالة الرئيسي حسب الحالة
        if status == 'في التحضير':
            body_text = f"مرحباً، طلبك رقم {order_name} قيد التحضير!"
        elif status == 'جاهز للتوصيل':
            body_text = f"مرحباً، طلبك رقم {order_name} جاهز الآن للتوصيل أو الاستلام من المعرض!"
        elif status == 'تم تسليمه للتوصيل':
            body_text = f"مرحباً، طلبك رقم {order_name} أصبح الآن مع شركة التوصيل!"
        else:
            body_text = f"مرحباً، تم تحديث حالة طلبك رقم {order_name} إلى: {status}"

        footer = "\n\nهذا الرقم مخصص للنشرات والرد الآلي، للطلب والاستفسار يرجى التواصل معنا على واتساب: 0780110417"
        message = body_text + footer

        if not phone_raw:
            logging.error("No phone number found in payload.")
            return jsonify({
                "status": "error", 
                "message": "No phone number provided in payload",
                "received_data": data
            }), 400

        # تنظيف رقم الهاتف وإبقاء الأرقام فقط
        clean_phone = re.sub(r'\D', '', str(phone_raw))
        chat_id = f"{clean_phone}@c.us"

        # رابط Green API مع رقم السيرفر الصحيح 7107
        url = f"https://7107.api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
        
        payload = {
            "chatId": chat_id,
            "message": message
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers)
        
        try:
            res_data = response.json()
        except Exception:
            res_data = response.text

        logging.info(f"Green API Response: {res_data}")
        return jsonify({"status": "success", "green_api_response": res_data}), response.status_code

    except Exception as e:
        logging.error(f"Error executing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
