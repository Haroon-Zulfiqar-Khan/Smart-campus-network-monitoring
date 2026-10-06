export const permissionLabels={tests:'View all network tests',complaints:'Review and update complaints',maintenance:'Write maintenance notes',locations:'Manage campus locations',reports:'View and export reports'};
export type Permission=keyof typeof permissionLabels;
export const defaultPermissions={'Student':[],'IT Support':['tests','complaints','maintenance'],'Manager':['reports'],'Administrator':['tests','complaints','maintenance','locations','reports']} as Record<string,Permission[]>;
