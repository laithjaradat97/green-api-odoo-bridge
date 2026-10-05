import os
import requests
import logging
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

@app.route('/send-invoice', methods=['POST'])
def send_invoice():
    try:
        # استبدال متغيرات UltraMsg بمتطلبات Green API
        GREEN_API_INSTANCE_ID = (os.environ.get('710722756916') or '').strip()
        GREEN_API_TOKEN = (os.environ.get('171a159febe044b987e0378fd3b6e006a1661f14a6a149ccbc') or '').strip()

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

        # 1. نص الرسالة الرئيسي حسب الحالة
        if status == 'في التحضير':
            body_text = f"مرحباً، طلبك رقم {order_name} قيد التحضير!"
        elif status == 'جاهز للتوصيل':
            body_text = f"مرحباً، طلبك رقم {order_name} جاهز الآن للتوصيل أو الاستلام من المعرض!"
        elif status == 'تم تسليمه للتوصيل':
            body_text = f"مرحباً، طلبك رقم {order_name} أصبح الآن مع شركة التوصيل!"
        else:
            body_text = f"مرحباً، تم تحديث حالة طلبك رقم {order_name} إلى: {status}"

        # 2. النص اللاحق (الخاتمة / الإضافة)
        footer = "\n\nهذا الرقم مخصص للنشرات والرد الآلي، للطلب والاستفسار يرجى التواصل معنا على واتساب: 0780110417"

        # دمج النص الرئيسي مع النص اللاحق
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
        
        # Green API يتطلب أن ينتهي رقم الواتساب بـ @c.us
        chat_id = f"{clean_phone}@c.us"

        # إرسال إلى Green API (الرابط وواجهة الـ Endpoint الخاصة بإرسال الرسائل)
        url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
        
        payload = {
            "chatId": chat_id,
            "message": message
        }
        
        headers = {'Content-Type': 'application/json'}
        
        # استخدام json=payload بدلاً من بيانات الـ form-urlencoded
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
