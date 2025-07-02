# frappe-bench/apps/invitation_system/invitation_system/api.py

import json
import secrets

import frappe
from frappe.utils import now_datetime


@frappe.whitelist(allow_guest=True)
def register_host():
	"""
	Public endpoint to register a new Host.
	"""
	data = frappe.form_dict

	if not all([data.get("email"), data.get("password"), data.get("host_name")]):
		frappe.throw("Email, Host Name, and Password are required.", frappe.MissingMandatoryError)

	if frappe.db.exists("Host Details", data.get("email")):
		frappe.throw(
			"An active host profile with this email already exists. Please log in or use 'Forgot Password'.",
			title="Profile Exists",
		)

	try:
		host_doc = frappe.get_doc(
			{
				"doctype": "Host Details",
				"host_name": data.get("host_name"),
				"email": data.get("email"),
				"mobile": data.get("mobile"),
				"password": data.get("password"),
			}
		)

		host_doc.insert(ignore_permissions=True)
		frappe.db.commit()

		return {
			"status": "success",
			"message": "Host registered successfully. You can now log in and verify your account.",
			"host_name": host_doc.name,
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "register_host_api_error")
		frappe.throw(f"An error occurred during registration: {e}")


@frappe.whitelist()
def send_verification_otp():
	"""
	Generates, saves, and emails a new OTP for the currently logged-in host.
	"""
	if frappe.session.user == "Guest":
		frappe.throw("You must be logged in to request an OTP.", frappe.PermissionError)

	try:
		host = frappe.get_doc("Host Details", {"user_id": frappe.session.user})
		if host.is_verified:
			return {"status": "info", "message": "Your account is already verified."}

		otp_code = str(secrets.randbelow(10**6)).zfill(6)

		otp_doc = frappe.get_doc(
			{
				"doctype": "OTP - PIN Request",
				"host": host.name,
				"request_type": "OTP",
				"code": otp_code,
				"requested_at": now_datetime(),
				"consumed": 0,
			}
		)
		otp_doc.insert(ignore_permissions=True)
		frappe.db.commit()

		subject = f"Your InvitationSystem Verification Code is {otp_code}"
		message = f"<h3>Hello {host.host_name},</h3><p>Your One-Time Password (OTP) is: <strong>{otp_code}</strong></p>"
		frappe.sendmail(recipients=[host.email], subject=subject, message=message, now=True)

		return {"status": "success", "message": f"An OTP has been sent to {host.email}."}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "send_otp_api_error")
		frappe.throw(f"An error occurred while sending the OTP: {e}")


@frappe.whitelist()
def verify_host():
	"""
	Verifies the OTP provided by the logged-in host.
	"""
	if frappe.session.user == "Guest":
		frappe.throw("You must be logged in to verify your account.", frappe.PermissionError)

	try:
		request_body = frappe.request.data.decode("utf-8")
		data = json.loads(request_body)
	except Exception:
		frappe.throw("Invalid request body. Expected JSON.", frappe.ValidationError)

	provided_otp = str(data.get("otp", ""))
	if not provided_otp:
		frappe.throw("OTP is required for verification.", frappe.MissingMandatoryError)

	try:
		host = frappe.get_doc("Host Details", {"user_id": frappe.session.user})

		latest_otp_doc_name = frappe.db.get_value(
			"OTP - PIN Request",
			{"host": host.name, "consumed": 0, "code": provided_otp},
			"name",
			order_by="creation desc",
		)

		if not latest_otp_doc_name:
			frappe.throw("Invalid OTP. Please try again or request a new one.", frappe.ValidationError)

		otp_doc = frappe.get_doc("OTP - PIN Request", latest_otp_doc_name)
		otp_doc.consumed = 1
		otp_doc.consumed_at = now_datetime()
		otp_doc.save(ignore_permissions=True)

		host.is_verified = 1
		host.save(ignore_permissions=True)
		frappe.db.commit()

		return {"status": "success", "message": "Account verified successfully."}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "verify_host_api_error")
		frappe.throw(f"An error occurred during verification: {e}")


@frappe.whitelist()
def get_current_host_details():
	"""
	Gets a specific subset of details for the currently logged-in host.
	"""
	if frappe.session.user == "Guest":
		frappe.throw("You must be logged in to view your details.", frappe.PermissionError)

	try:
		host_doc = frappe.get_doc("Host Details", {"user_id": frappe.session.user})
		return {
			"host_name": host_doc.host_name,
			"email": host_doc.email,
			"mobile": host_doc.mobile,
			"is_verified": host_doc.is_verified,
			"user_id": host_doc.name,
		}
	except frappe.DoesNotExistError:
		frappe.throw("No Host Details record found for the current user.", frappe.NotFoundError)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_current_host_details_api_error")
		frappe.throw(f"An error occurred while fetching details: {e}")


@frappe.whitelist()
def update_host_profile():
	"""
	Authenticated endpoint for a logged-in host to update their own profile details.
	"""
	if frappe.session.user == "Guest":
		frappe.throw("You must be logged in to update your profile.", frappe.PermissionError)

	try:
		data = json.loads(frappe.request.data.decode("utf-8"))
	except Exception:
		frappe.throw("Invalid request body. Expected JSON.", frappe.ValidationError)

	try:
		host_doc = frappe.get_doc("Host Details", {"user_id": frappe.session.user})
		user_doc = frappe.get_doc("User", frappe.session.user)
		updated = False

		if "host_name" in data and data["host_name"] != host_doc.host_name:
			host_doc.host_name = data["host_name"]
			user_doc.first_name = data["host_name"]
			updated = True

		if "mobile" in data and data["mobile"] != host_doc.mobile:
			host_doc.mobile = data["mobile"]
			user_doc.mobile_no = data["mobile"]
			updated = True

		if not updated:
			return {"status": "no-change", "message": "No new data provided to update."}

		host_doc.save(ignore_permissions=True)
		user_doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {"status": "success", "message": "Profile updated successfully."}
	except frappe.DoesNotExistError:
		frappe.throw("No Host Details record found for the current user.", frappe.NotFoundError)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "update_host_profile_api_error")
		frappe.throw(f"An error occurred while updating the profile: {e}")
