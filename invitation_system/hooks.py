# frappe-bench/apps/invitation_system/invitation_system/hooks.py

app_name = "invitation_system"
app_title = "Invitation System"
app_publisher = "Your Name"
app_description = "An online platform for managing event invitations."
app_email = "your.email@example.com"
app_license = "MIT"

# # Schedulers
# scheduler_events = {
#     "daily": [
#         "invitation_system.doctype.orders.orders.send_pre_invites_daily",
#         "invitation_system.doctype.orders.orders.send_invites_daily",
#         "invitation_system.doctype.orders.orders.send_reminders_daily",
#         "invitation_system.doctype.orders.orders.send_thank_you_messages_daily",
#     ]
# }

# Custom API Endpoints
api_methods = [
	"invitation_system.api.register_host",
	"invitation_system.api.get_current_host_details",
	"invitation_system.api.send_verification_otp",
	"invitation_system.api.verify_host",
	"invitation_system.api.update_host_profile",
]

fixtures = ["Base Packs"]
# Note: You can add other hooks like doctype_events if needed, for example:
# doctype_events = {
# 	"Host Details": {
# 		"on_update": "path.to.handler.function"
# 	}
# }
