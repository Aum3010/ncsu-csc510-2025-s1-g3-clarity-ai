import {
  type RouteConfig,
  route,
  index,
  layout,
  prefix,
} from "@react-router/dev/routes"; // Import from the package you are using


export default [
  // The Root Layout (This will be the App component structure, hosting the Sidebar)
  layout("./App.jsx", [
    
    // The Dashboard Index Route (The default page rendered at /)
    index("./views/RequirementsDashboard.jsx"),

    // Other Navigation Links (Placeholder)
    route("documents", "./views/Documents.jsx"),
    route("integrations", "./views/Integrations.jsx"),
    route("team", "./views/Team.jsx"),

    // route("requirement/:reqId", "./views/RequirementDetail.jsx"),
  ]),
] satisfies RouteConfig;