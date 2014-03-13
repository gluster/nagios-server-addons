glusternagiosconfdir = $(sysconfdir)/nagios/gluster
glusternagiosconf_DATA = \
	gluster-commands.cfg \
	gluster-host-groups.cfg \
	gluster-host-services.cfg \
	gluster-templates.cfg \
	gluster-contacts.cfg \
        $(NULL)

glusternagiosdefaultconfdir = $(sysconfdir)/nagios/gluster/default
glusternagiosdefaultconf_DATA = \
	node1.cfg \
        $(NULL)

EXTRA_DIST = \
	$(glusternagiosconf_DATA) \
	$(glusternagiosdefaultconf_DATA) \
        $(NULL)
