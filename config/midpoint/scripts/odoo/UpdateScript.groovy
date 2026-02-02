import org.identityconnectors.framework.common.objects.Attribute
import org.identityconnectors.framework.common.objects.AttributesAccessor
import org.identityconnectors.framework.common.objects.Uid

// Chargement du helper
evaluate(new File(scriptPath + '/OdooHelper.groovy'))

log.info("Updating Odoo user ID: {0}", uid.uidValue)

try {
    def odoo = new OdooHelper(
        configuration.serviceAddress,
        configuration.username,
        configuration.password.toString()
    )
    
    def accessor = new AttributesAccessor(attributes as Set<Attribute>)
    def userId = uid.uidValue as Integer
    
    // Récupération des attributs à mettre à jour
    def updates = [:]
    
    // Nom complet
    def name = accessor.findString("name")
    if (name) {
        updates.name = name
    }
    
    // Email
    def email = accessor.findString("email")
    if (email) {
        updates.email = email
    }
    
    // Statut actif
    def active = accessor.findBoolean("active")
    if (active != null) {
        updates.active = active
    }
    
    // Groupes
    def groups = accessor.findList("groups_id")
    if (groups && groups.size() > 0) {
        updates.groups_id = [[6, 0, groups]] // Remplacer tous les groupes
    }
    
    if (updates.size() > 0) {
        log.info("Updating user {0} with: {1}", userId, updates)
        
        odoo.write('res.users', [userId], updates)
        
        log.info("✓ User updated successfully")
    } else {
        log.info("No updates to apply")
    }
    
    return uid
    
} catch (Exception e) {
    log.error("✗ Failed to update user: {0}", e.message)
    throw e
}
