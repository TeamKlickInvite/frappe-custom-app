# invitation_system/invitation_system/doctype/host_details/host_details.py
import frappe
from frappe.model.document import Document

class HostDetails(Document):
    def before_insert(self):
        """
        This hook handles the creation/re-activation of a User when a new Host Details record is created.
        It now also syncs the mobile number.
        """
        if frappe.db.exists("Host Details", self.email):
            frappe.throw(
                f"An active host profile with the email '{self.email}' already exists. Please log in or use 'Forgot Password'.",
                title="Profile Exists"
            )

        self.owner = self.email
        
        if frappe.db.exists("User", self.email):
            # --- SCENARIO A: User exists (re-registering) ---
            try:
                user = frappe.get_doc("User", self.email)
                user.first_name = self.host_name
                user.enabled = 1
                user.new_password = self.password
                user.mobile_no = self.mobile 
                # self.phone = self.mobile # <-- ADDED: Sync mobile number on update
                
                user.flags.ignore_permissions = True
                user.save(ignore_permissions=True)
                
                self.user_id = user.name
                frappe.msgprint(f"Existing User {user.name} was re-activated and updated.", indicator="green")
            
            except Exception as e:
                frappe.log_error(f"Failed to re-activate user {self.email}: {e}", "Host Details Re-registration")
                frappe.throw(f"An error occurred while re-activating the user profile.")
        
        else:
            # --- SCENARIO B: User does not exist (new registration) ---
            try:
                user = frappe.get_doc({
                    "doctype": "User",
                    "email": self.email,
                    "first_name": self.host_name,
                    "user_type": "Website User",
                    "roles": [{"role": "Host"}],
                    "send_welcome_email": 0,
                    "enabled": 1,
                    "new_password": self.password,
                    "mobile_no": self.mobile ,
                    # "phone" : self.mobile 
                      # <-- ADDED: Sync mobile number on creation
                })
                
                user.flags.ignore_permissions = True
                user.insert(ignore_permissions=True)
                
                self.user_id = user.name
                frappe.msgprint(f"New User {user.name} created and ownership set successfully.", indicator="green")
            
            except Exception as e:
                frappe.log_error(f"Failed to create new user for host {self.name}: {e}", "Host Details Registration")
                frappe.throw(f"Failed to create linked user: {e}")

    def before_update(self):
        """
        This hook prevents critical, linked fields from being changed
        and syncs the mobile number if it's updated on the Host Details page.
        """
        if self.has_value_changed("email"):
            frappe.throw("The email address cannot be changed after registration.", title="Update Not Allowed")

        if self.has_value_changed("user_id"):
            frappe.throw("The linked User ID cannot be changed.", title="Update Not Allowed")

        # Sync mobile number to User doctype if it changes
        if self.has_value_changed("mobile") and self.user_id:
            try:
                frappe.db.set_value("User", self.user_id, "mobile_no", self.mobile)
                # frappe.db.set_value("User", self.user_id, "phone", self.mobile)
                
                frappe.msgprint("Mobile number synced to User profile.", indicator="green")
            except Exception as e:
                frappe.log_error(f"Failed to sync mobile number for User {self.user_id}", "Host Details Update")


    def on_trash(self):
        """
        This hook triggers right before the document is permanently deleted.
        We will disable the linked Frappe User instead of deleting them.
        """
        if not self.user_id:
            return

        try:
            user_doc = frappe.get_doc("User", self.user_id)
            user_doc.enabled = 0
            user_doc.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.msgprint(f"User {self.user_id} has been disabled.", indicator="orange")
        except frappe.DoesNotExistError:
            frappe.log_error(f"User {self.user_id} not found during Host Details deletion.", "on_trash hook")
        except Exception as e:
            frappe.log_error(f"An error occurred while disabling user {self.user_id}: {e}", "on_trash hook")