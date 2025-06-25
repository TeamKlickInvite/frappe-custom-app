# invitation_system/invitation_system/api.py
import frappe

@frappe.whitelist(allow_guest=True)
def register_host():
    """
    Public endpoint to register a new Host.
    This creates both a 'Host Details' record AND a Frappe 'User' record simultaneously.
    """
    data = frappe.form_dict

    if not all([data.get('email'), data.get('password'), data.get('host_name')]):
        frappe.throw("Email, Host Name, and Password are required.", frappe.MissingMandatoryError)
    
    if frappe.db.exists("Host Details", data.get('email')):
        frappe.throw(f"A host with the email '{data.get('email')}' already exists.", frappe.DuplicateEntryError)

    try:
        # The 'before_insert' hook in 'host_details.py' will now handle User creation.
        host_doc = frappe.get_doc({
            "doctype": "Host Details",
            "host_name": data.get('host_name'),
            "email": data.get('email'),
            "mobile": data.get('mobile'),
            "password": data.get('password') # Stored as-is on Host Details
        })
        
        host_doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": "Host registered successfully. You can now log in and verify your account.",
            "host_name": host_doc.name
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'register_host_api_error')
        frappe.throw(f"An error occurred during registration: {e}")

@frappe.whitelist()
def verify_host():
    """
    Authenticated endpoint for a logged-in Host to verify their account with an OTP.
    Method: POST
    Form Data: otp
    """
    if frappe.session.user == "Guest":
        frappe.throw("You must be logged in to verify your account.", frappe.PermissionError)

    data = frappe.form_dict
    provided_otp = data.get('otp')
    
    # --- Hardcoded OTP for testing ---
    # In a real application, this would be generated, stored with an expiry, and sent via SMS/Email.
    hardcoded_otp = "123456"

    # --- Debugging: Log the provided and expected passwords/OTPs ---
    frappe.log_error(
        title="Host Verification Attempt",
        message=f"User: {frappe.session.user}, Provided OTP: {provided_otp}, Expected OTP: {hardcoded_otp}"
    )

    if not provided_otp:
        frappe.throw("OTP is required for verification.", frappe.MissingMandatoryError)

    if provided_otp != hardcoded_otp:
        frappe.throw("Invalid OTP provided.", frappe.ValidationError)

    try:
        # Get the Host Details document for the logged-in user
        host_doc = frappe.get_doc("Host Details", {"user_id": frappe.session.user})
        
        if host_doc.is_verified:
            return {"status": "info", "message": "Account is already verified."}

        # Set the verified flag and save the document
        host_doc.is_verified = 1
        host_doc.save(ignore_permissions=True) # Ignore permissions because the host might not have write access after certain workflows
        frappe.db.commit()

        return {
            "status": "success",
            "message": "Account verified successfully."
        }
    except frappe.DoesNotExistError:
        frappe.throw("No Host Details record found for the current user.", frappe.NotFoundError)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'verify_host_api_error')
        frappe.throw(f"An error occurred during verification: {e}")

@frappe.whitelist()
def get_current_host_details():
    """
    Endpoint for a logged-in Host to get their own details.
    Method: GET
    """
    if frappe.session.user == "Guest":
        frappe.throw("You must be logged in to view your details.", frappe.PermissionError)

    try:
        host_doc = frappe.get_doc("Host Details", {"user_id": frappe.session.user})
        
        response_data = host_doc.as_dict()
        if 'password' in response_data:
            del response_data['password']

        return response_data
    
    except frappe.DoesNotExistError:
        frappe.throw("No Host Details record found for the current user.", frappe.NotFoundError)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'get_current_host_details_api_error')
        frappe.throw(f"An error occurred while fetching details: {e}")
