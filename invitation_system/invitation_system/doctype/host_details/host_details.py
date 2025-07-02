# frappe-bench/apps/invitation_system/invitation_system/doctype/host_details/host_details.py

import frappe
from frappe.model.document import Document


class HostDetails(Document):
	def before_insert(self):
		"""
		Handles the creation/re-activation of a User when a new Host Details record is created.
		It also syncs the mobile number to the User doctype.
		"""
		# 1. Block creation if an active host profile already exists.
		if frappe.db.exists("Host Details", self.email):
			frappe.throw(
				f"An active host profile with the email '{self.email}' already exists. Please log in or use 'Forgot Password'.",
				title="Profile Exists",
			)

		# 2. Set the owner of this new Host Details document to the user themselves.
		self.owner = self.email

		# 3. Check if a User document exists for this email to handle re-registration.
		if frappe.db.exists("User", self.email):
			# --- SCENARIO A: User exists (they are re-registering) ---
			try:
				user = frappe.get_doc("User", self.email)
				user.first_name = self.host_name
				user.enabled = 1
				user.new_password = self.password
				user.mobile_no = self.mobile

				user.flags.ignore_permissions = True
				user.save(ignore_permissions=True)

				self.user_id = user.name
				frappe.msgprint(f"Existing User {user.name} was re-activated and updated.", indicator="green")

			except Exception as e:
				frappe.log_error(
					f"Failed to re-activate user {self.email}: {e}", "Host Details Re-registration"
				)
				frappe.throw("An error occurred while re-activating the user profile.")

		else:
			# --- SCENARIO B: User does not exist (a truly new registration) ---
			try:
				user = frappe.get_doc(
					{
						"doctype": "User",
						"email": self.email,
						"first_name": self.host_name,
						"user_type": "Website User",
						"roles": [{"role": "Host"}],
						"send_welcome_email": 0,
						"enabled": 1,
						"new_password": self.password,
						"mobile_no": self.mobile,
					}
				)

				user.flags.ignore_permissions = True
				user.insert(ignore_permissions=True)

				self.user_id = user.name
				frappe.msgprint(
					f"New User {user.name} created and ownership set successfully.", indicator="green"
				)

			except Exception as e:
				frappe.log_error(
					f"Failed to create new user for host {self.name}: {e}", "Host Details Registration"
				)
				frappe.throw(f"Failed to create linked user: {e}")

	def before_update(self):
		"""
		Prevents critical, linked fields from being changed and syncs the mobile number if it's updated.
		"""
		if self.has_value_changed("email"):
			frappe.throw(
				"The email address cannot be changed after registration.", title="Update Not Allowed"
			)

		if self.has_value_changed("user_id"):
			frappe.throw("The linked User ID cannot be changed.", title="Update Not Allowed")

	def on_trash(self):
		"""
		Triggers before the document is deleted to disable the linked Frappe User.
		"""
		if not self.user_id:
			return

		try:
			user_doc = frappe.get_doc("User", self.user_id)
			if user_doc.enabled:
				user_doc.enabled = 0
				user_doc.save(ignore_permissions=True)
				frappe.db.commit()
				frappe.msgprint(f"User {self.user_id} has been disabled.", indicator="orange")

		except frappe.DoesNotExistError:
			frappe.log_error(f"User {self.user_id} not found during Host Details deletion.", "on_trash hook")
		except Exception as e:
			frappe.log_error(f"An error occurred while disabling user {self.user_id}: {e}", "on_trash hook")
