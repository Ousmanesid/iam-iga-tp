import org.apache.xmlrpc.client.XmlRpcClient
import org.apache.xmlrpc.client.XmlRpcClientConfigImpl

/**
 * Helper class pour l'API XML-RPC d'Odoo
 */
class OdooHelper {
    
    def url
    def database = "odoo"
    def username
    def password
    def uid
    
    def commonClient
    def objectClient
    
    OdooHelper(String url, String username, String password) {
        this.url = url.replaceAll('/$', '')
        this.username = username
        this.password = password
        
        // Configuration XML-RPC pour common
        def commonConfig = new XmlRpcClientConfigImpl()
        commonConfig.setServerURL(new URL("${this.url}/xmlrpc/2/common"))
        this.commonClient = new XmlRpcClient()
        this.commonClient.setConfig(commonConfig)
        
        // Configuration XML-RPC pour object
        def objectConfig = new XmlRpcClientConfigImpl()
        objectConfig.setServerURL(new URL("${this.url}/xmlrpc/2/object"))
        this.objectClient = new XmlRpcClient()
        this.objectClient.setConfig(objectConfig)
        
        this.authenticate()
    }
    
    /**
     * Authentification auprès d'Odoo via XML-RPC
     */
    def authenticate() {
        try {
            this.uid = commonClient.execute("authenticate", [
                database,
                username,
                password,
                [:] // Empty map for context
            ])
            
            if (this.uid) {
                log.info("✓ Authenticated as user ID: {0}", uid)
                return uid
            } else {
                throw new RuntimeException("Authentication failed: uid is null")
            }
        } catch (Exception e) {
            log.error("✗ Authentication error: {0}", e.message)
            throw e
        }
    }
    
    /**
     * Appel XML-RPC générique à execute_kw
     */
    def executeKw(String model, String method, List args, Map kwargs = [:]) {
        return objectClient.execute("execute_kw", [
            database,
            uid,
            password,
            model,
            method,
            args,
            kwargs
        ])
    }
    
    /**
     * Recherche d'enregistrements avec search_read
     */
    def search(String model, List domain = [], Map options = [:]) {
        def kwargs = [:]
        
        if (options.fields) {
            kwargs.fields = options.fields
        }
        if (options.limit && options.limit > 0) {
            kwargs.limit = options.limit
        }
        if (options.offset && options.offset > 0) {
            kwargs.offset = options.offset
        }
        
        return executeKw(model, "search_read", [domain], kwargs)
    }
    
    /**
     * Création d'un enregistrement
     */
    def create(String model, Map values) {
        return executeKw(model, "create", [[values]])
    }
    
    /**
     * Mise à jour d'un enregistrement
     */
    def write(String model, List ids, Map values) {
        return executeKw(model, "write", [ids, values])
    }
    
    /**
     * Lecture d'enregistrements
     */
    def read(String model, List ids, List fields = []) {
        def kwargs = fields ? [fields: fields] : [:]
        return executeKw(model, "read", [ids], kwargs)
    }
    
    /**
     * Recherche d'IDs uniquement
     */
    def searchIds(String model, List domain = [], Integer limit = 0) {
        def kwargs = limit > 0 ? [limit: limit] : [:]
        return executeKw(model, "search", [domain], kwargs)
    }
}
