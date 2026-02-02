import org.identityconnectors.framework.common.objects.Attribute
import org.identityconnectors.framework.common.objects.AttributesAccessor
import org.identityconnectors.framework.common.objects.Uid

// Chargement du helper
evaluate(new File(scriptPath + '/OdooHelper.groovy'))

log.info("Creating Odoo user: {0}", id)

try {
    def odoo = new OdooHelper(
        configuration.serviceAddress,
        configuration.username,
        configuration.password.toString()
    )
    
    def accessor = new AttributesAccessor(attributes as Set<Attribute>)
    
    // Récupération des attributs
    def login = id // __NAME__ = login
    def name = accessor.findString("name")
    def email = accessor.findString("email")
    def active = accessor.findBoolean("active") ?: true
    def groups = accessor.findList("groups_id") ?: []
    
    log.info("User details - Login: {0}, Name: {1}, Email: {2}", login, name, email)
    
    // 1. Trouver le groupe "Internal User" (base.group_user)
    def groupIds = []
    
    // Chercher le groupe via la référence externe
    def groupRefs = odoo.search('ir.model.data', 
        [['module', '=', 'base'], ['name', '=', 'group_user'], ['model', '=', 'res.groups']], 
        [fields: ['res_id'], limit: 1]
    )
    
    if (groupRefs && groupRefs.size() > 0) {
        def groupId = groupRefs[0].res_id
        groupIds = [[6, 0, [groupId]]] // Format Odoo : [(6, 0, [ids])]
        log.info("✓ Found Internal User group ID: {0}", groupId)
    } else {
        // Fallback : recherche directe (si le champ name existe)
        log.warn("Could not find group via external ID, trying direct search...")
    }
    
    // 2. Créer l'utilisateur
    def userValues = [
        login: login,
        name: name,
        email: email,
        active: active,
        notification_type: 'inbox' // Notifications internes uniquement
        // Pas de password : l'utilisateur se connectera via LDAP
    ]
    
    // Ajouter les groupes seulement si trouvés
    if (groupIds.size() > 0) {
        userValues.groups_id = groupIds
    }
    
    log.info("Creating user with values: {0}", userValues)
    
    def userId = odoo.create('res.users', userValues)
    
    log.info("✓ User created successfully with ID: {0}", userId)
    
    // Retourner l'UID
    return new Uid(userId.toString())
    
} catch (Exception e) {
    log.error("✗ Failed to create user: {0}", e.message)
    log.error("Stack trace: {0}", e.getStackTrace())
    throw e
}
