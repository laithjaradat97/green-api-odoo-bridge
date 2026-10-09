import os
import requests
import logging
import re
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

def send_whatsapp_async(data, green_api_id, green_api_token):
    """دالة تعمل في الخلفية لإرسال رسالة الواتساب عبر Green API دون إبطاء الاستجابة"""
    try:
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
            return

        # تنظيف رقم الهاتف وإبقاء الأرقام فقط
        clean_phone = re.sub(r'\D', '', str(phone_raw))
        chat_id = f"{clean_phone}@c.us"

        # رابط Green API مع رقم السيرفر الصحيح 7107
        url = f"https://7107.api.green-api.com/waInstance{green_api_id}/sendMessage/{green_api_token}"
        
        payload = {
            "chatId": chat_id,
            "message": message
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers)
        logging.info(f"Green API Background Response: {response.text}")

    except Exception as e:
        logging.error(f"Error in background worker: {str(e)}")

@app.route('/send-invoice', methods=['POST', 'GET'])
def send_invoice():
    # في حال طلب التنشيط بطريقة GET
    if request.method == 'GET':
        return jsonify({"status": "active", "message": "Server is awake and running!"}), 200

    try:
        GREEN_API_INSTANCE_ID = (os.environ.get('GREEN_API_INSTANCE_ID') or '').strip()
        GREEN_API_TOKEN = (os.environ.get('GREEN_API_TOKEN') or '').strip()

        data = request.json or {}
        logging.info(f"Received payload from Odoo: {data}")
        
        # تشغيل عملية الإرسال في خيط (Thread) منفصل بالخلفية لضمان الرد الفوري على أودو
        thread = threading.Thread(
            target=send_whatsapp_async, 
            args=(data, GREEN_API_INSTANCE_ID, GREEN_API_TOKEN)
        )
        thread.start()

        # الرد الفوري على أودو لمنع أي Timeout
        return jsonify({"status": "success", "message": "Webhook received and processing"}), 200

    except Exception as e:
        logging.error(f"Error executing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
