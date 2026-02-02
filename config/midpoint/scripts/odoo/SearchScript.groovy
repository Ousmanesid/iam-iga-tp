import org.identityconnectors.framework.common.objects.ObjectClass
import org.identityconnectors.framework.common.objects.OperationOptions
import org.identityconnectors.framework.common.objects.ConnectorObjectBuilder
import org.identityconnectors.framework.common.objects.AttributeBuilder

// Chargement du helper
evaluate(new File(scriptPath + '/OdooHelper.groovy'))

log.info("Searching Odoo users with query: {0}", query)

try {
    def odoo = new OdooHelper(
        configuration.serviceAddress,
        configuration.username,
        configuration.password.toString()
    )
    
    // Construction du domaine de recherche
    def domain = []
    
    // Exclure les utilisateurs système
    domain.add(['login', '!=', 'admin'])
    domain.add(['login', '!=', '__system__'])
    
    // Si un query est fourni (recherche par login)
    if (query && query.operation && query.operation == "EQUALS") {
        if (query.get("__NAME__")) {
            domain.add(['login', '=', query.get("__NAME__")])
        } else if (query.get("__UID__")) {
            domain.add(['id', '=', query.get("__UID__") as Integer])
        }
    }
    
    log.info("Search domain: {0}", domain)
    
    // Recherche des utilisateurs
    def users = odoo.search('res.users', domain, [
        fields: ['id', 'login', 'name', 'email', 'active', 'partner_id', 'groups_id'],
        limit: options?.pageSize ?: 100
    ])
    
    log.info("Found {0} users", users.size())
    
    // Conversion en ConnectorObject
    users.each { user ->
        def builder = new ConnectorObjectBuilder()
        builder.setObjectClass(ObjectClass.ACCOUNT)
        builder.setUid(user.id.toString())
        builder.setName(user.login)
        
        builder.addAttribute("name", user.name)
        builder.addAttribute("email", user.email ?: "")
        builder.addAttribute("active", user.active ?: false)
        builder.addAttribute("partner_id", user.partner_id ? user.partner_id[0] : null)
        
        // Groupes (liste d'IDs)
        if (user.groups_id && user.groups_id.size() > 0) {
            builder.addAttribute("groups_id", user.groups_id)
        }
        
        handler(builder.build())
    }
    
    log.info("✓ Search completed")
    
} catch (Exception e) {
    log.error("✗ Search failed: {0}", e.message)
    throw e
}
