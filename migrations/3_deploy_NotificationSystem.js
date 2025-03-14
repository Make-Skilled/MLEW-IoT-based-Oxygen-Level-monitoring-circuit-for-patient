const NotificationSystem=artifacts.require("NotificationSystem");

module.exports=function(deployer){
    deployer.deploy(NotificationSystem);
}