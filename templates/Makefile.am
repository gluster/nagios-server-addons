pnp4nagioscheckcommanddir = $(sysconfdir)/pnp4nagios/check_commands
pnp4nagioscheckcommand_DATA = \
	check_brick_usage.cfg \
	check_disk_and_inode.cfg \
	check_interfaces.cfg \
	$(NULL)

pnp4nagiostemplatedir = $(datarootdir)/nagios/html/pnp4nagios/templates.dist
pnp4nagiostemplate_DATA = \
	check_cluster_vol_usage.php \
	check_cpu_multicore.php \
	check_disk_and_inode.php \
	check_interfaces.php \
	check_memory.php \
	check_swap_usage.php \
	check_vol_utilization.php \
	check_brick_usage.php \
        $(NULL)

EXTRA_DIST = \
	$(pnp4nagioscheckcommand_DATA) \
	$(pnp4nagiostemplate_DATA) \
        $(NULL)
