//
//  AuctionSampleAppDelegate.h
//  AuctionSample
//
//  Created by Peter Georgeson on 18/05/11.
//  Copyright 2011 __MyCompanyName__. All rights reserved.
//

#import <UIKit/UIKit.h>

@class AuctionSampleViewController;

@interface AuctionSampleAppDelegate : NSObject <UIApplicationDelegate> {

}

@property (nonatomic, retain) IBOutlet UIWindow *window;

@property (nonatomic, retain) IBOutlet AuctionSampleViewController *viewController;

@end
