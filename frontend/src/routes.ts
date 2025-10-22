import {
  type RouteConfig,
  route,
  index,
  layout,
  prefix,
} from "@react-router/dev/routes"; // Import from the package you are using


export default [
  layout("./App.jsx", [
    
    index("./views/RequirementsDashboard.jsx"),
    route("documents", "./views/Documents.jsx"),
    route("integrations", "./views/Integrations.jsx"),
    route("team", "./views/Team.jsx"),
  ]),
] satisfies RouteConfig;