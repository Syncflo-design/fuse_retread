app_name        = "fuse_retread"
app_title       = "Fuse Retread"
app_publisher   = "Syncflo"
app_description = "Tyre retreading for Fuse: every tyre traced from the branch, through the factory and back to its owner, on simple floor screens."
app_email       = "ops@syncflo.co.za"
app_license     = "MIT"

# ERPNext for Customer and Company; fuse_core for the module switches. Deliberately NOT
# fuse_manufacturing: a customer's tyre is not the retreader's own stock, so nothing here moves
# ERPNext stock or posts through the manufacturing path.
required_apps = ["erpnext", "fuse_core"]

# The two roles must exist before the doctypes that name them are synced.
before_install = "fuse_retread.install.before_install"
# Both, and fuse_retread.install.after_install by hand as well: after_migrate has been seen
# not to fire on a Frappe Cloud deploy. Everything in it is idempotent.
after_install = "fuse_retread.install.after_install"
after_migrate = "fuse_retread.install.after_install"

# How this app reaches Fuse: its switch (Active Modules on Intacct Settings) and its tiles on
# Fuse Home. Callables, so the hook values merge as plain strings.
fuse_modules = ["fuse_retread.registry.get_modules"]
fuse_tiles = ["fuse_retread.registry.get_tiles"]

# Nothing here posts through a transaction definition yet. The invoice is a preview.
fuse_processes = []

# Tells the desk whether this is the Fuse demo site, so the demo loader's menu item appears
# there and on no client's site.
extend_bootinfo = "fuse_retread.demo.retread.boot"
