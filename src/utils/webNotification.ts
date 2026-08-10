export const isNotificationSupported = (): boolean => {
  return typeof window !== 'undefined' && 'Notification' in window;
};

export const getNotificationPermission = (): NotificationPermission => {
  if (!isNotificationSupported()) return 'denied';
  return Notification.permission;
};

export const requestNotificationPermission = async (): Promise<NotificationPermission> => {
  if (!isNotificationSupported()) return 'denied';
  try {
    const permission = await Notification.requestPermission();
    return permission;
  } catch (error) {
    console.error('Failed to request notification permission:', error);
    return 'denied';
  }
};

export const sendWebNotification = (title: string, options?: NotificationOptions): Notification | null => {
  if (!isNotificationSupported()) return null;

  if (Notification.permission === 'granted') {
    try {
      return new Notification(title, {
        icon: '/favicon.svg',
        badge: '/favicon.svg',
        tag: options?.tag || `apex-${Date.now()}`,
        ...options,
      });
    } catch (e) {
      console.error('Error instantiating Web Notification:', e);
      return null;
    }
  }
  return null;
};
