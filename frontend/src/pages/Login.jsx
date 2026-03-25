import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    navigate('/');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 py-12 px-4 sm:px-6 lg:px-8">
      <div className="absolute inset-0 z-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/10 via-background to-background"></div>
      
      <Card className="w-full max-w-md z-10 border-primary/20 bg-background/95 backdrop-blur shadow-2xl">
        <CardHeader className="space-y-1 flex flex-col items-center">
          <div className="mb-4 h-16 w-16 bg-primary/10 rounded-full flex items-center justify-center border border-primary/20">
            <Shield className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl text-center font-bold tracking-tight">BehaviorGuard Sign In</CardTitle>
          <CardDescription className="text-center">
            Enter your credentials to access the security portal.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70" htmlFor="email">
                Email / Username
              </label>
              <input
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                id="email"
                placeholder="admin@behaviorguard.ai"
                type="email"
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70" htmlFor="password">
                Password
              </label>
              <input
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                id="password"
                type="password"
                required
              />
            </div>
            <Button className="w-full mt-6" type="submit">
              Sign In
            </Button>
          </form>
          <div className="mt-4 text-center text-sm text-muted-foreground">
            Mock authentication (click Sign In to continue)
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
