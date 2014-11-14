glusternagiosconfdir = $(sysconfdir)/nagios/gluster
glusternagiosconf_DATA = \
	gluster-commands.cfg \
	gluster-host-groups.cfg \
	gluster-host-services.cfg \
	gluster-templates.cfg \
	gluster-contacts.cfg \
	host-monitoring-services.in \
	snmpmanagers.conf \
        $(NULL)

glusternagiosdefaultconfdir = $(sysconfdir)/nagios/gluster/default
glusternagiosdefaultconf_DATA = \
	glustercluster.cfg.sample \
	temp_node1.cfg \
        $(NULL)

glusternagiosmibsdir = /usr/share/snmp/mibs
glusternagiosmibs_DATA = \
	NAGIOS-NOTIFY-MIB \
	NAGIOS-ROOT-MIB \
        $(NULL)

sudodir = $(sysconfdir)/sudoers.d/
sudo_DATA = \
	nagios \
	$(NULL)

EXTRA_DIST = \
	$(glusternagiosconf_DATA) \
	$(glusternagiosdefaultconf_DATA) \
	$(glusternagiosmibs_DATA) \
	$(sudo_DATA) \
        $(NULL)
