<html><body>
<?php
$id = $_GET['id'];
$r = mysql_query("SELECT * FROM t WHERE id=$id");
echo $_GET['name'];
$q = "SELECT a FROM b WHERE c='" . $_POST['c'] . "'";
$h = md5($pw);
include($_GET['page']);
?>
<p>Don't worry, it's fine</p>
<?php if ($x) { ?> yes <?php } ?>
</body></html>
