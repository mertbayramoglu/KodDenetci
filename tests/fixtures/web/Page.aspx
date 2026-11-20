<%@ Page ValidateRequest="false" %>
<%-- <%= Request["x"] %> --%>
<div><%= Request["name"] %></div>
<%
  Response.Write(Request["q"]);
